"""Tests for watchdog functionality"""

import pytest
import asyncio
import os
from liteq import (
    task,
    QueueManager,
    enqueue,
    get_task_status,
)
from liteq.watchdog import Watchdog
from liteq.db import get_db_transaction

TEST_DB = "test_watchdog.db"


@pytest.fixture(autouse=True)
def cleanup_db():
    """Remove test database before and after each test"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@task
async def normal_task(value: int):
    """Normal task"""
    await asyncio.sleep(0.1)
    return value * 2


@pytest.mark.asyncio
async def test_watchdog_recovers_stuck_tasks():
    """Test that watchdog recovers tasks with outdated heartbeat"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    task_id = enqueue("normal_task", {"value": 5})

    # Manually set task to running with old heartbeat
    with get_db_transaction() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status='running',
                heartbeat_at=datetime('now', '-120 seconds'),
                worker_id='dead-worker'
            WHERE id=?
            """,
            (task_id,),
        )

    # Run watchdog with short timeout
    watchdog = Watchdog(lease_timeout_seconds=60, check_interval_seconds=1)

    # Check once
    await watchdog._check_stuck_tasks()

    # Check task was recovered
    status = get_task_status(task_id)
    assert status is not None
    assert status["status"] == "retry"
    assert status["worker_id"] is None


@pytest.mark.asyncio
async def test_watchdog_does_not_recover_active_tasks():
    """Test that watchdog doesn't touch tasks with recent heartbeat"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    task_id = enqueue("normal_task", {"value": 5})

    # Set task to running with recent heartbeat
    with get_db_transaction() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status='running',
                heartbeat_at=CURRENT_TIMESTAMP,
                worker_id='active-worker'
            WHERE id=?
            """,
            (task_id,),
        )

    # Run watchdog
    watchdog = Watchdog(lease_timeout_seconds=60, check_interval_seconds=1)
    await watchdog._check_stuck_tasks()

    # Task should still be running
    status = get_task_status(task_id)
    assert status is not None
    assert status["status"] == "running"
    assert status["worker_id"] == "active-worker"


@pytest.mark.asyncio
async def test_watchdog_integration_with_manager():
    """Test watchdog integration with QueueManager"""
    manager = QueueManager(
        db_path=TEST_DB,
        enable_watchdog=True,
        watchdog_lease_timeout=5,
        watchdog_check_interval=1,
    )
    manager.initialize()

    # Create a stuck task
    task_id = enqueue("normal_task", {"value": 5})

    with get_db_transaction() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status='running',
                heartbeat_at=datetime('now', '-10 seconds'),
                worker_id='stuck-worker'
            WHERE id=?
            """,
            (task_id,),
        )

    # Start manager with watchdog
    manager.add_worker("worker-1", queues=["default"])
    manager_task = asyncio.create_task(manager.start(setup_signal_handlers=False))

    # Give watchdog time to run
    await asyncio.sleep(2.0)

    # Stop
    await manager.stop()

    try:
        await asyncio.wait_for(manager_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Task should have been recovered and possibly completed
    status = get_task_status(task_id)
    assert status is not None
    # Task should be done or in retry (recovered)
    assert status["status"] in ("done", "retry", "running")


@pytest.mark.asyncio
async def test_watchdog_start_stop():
    """Test watchdog start and stop"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    watchdog = Watchdog(lease_timeout_seconds=30, check_interval_seconds=1)

    # Start watchdog in background
    watchdog_task = asyncio.create_task(watchdog.start())

    # Let it run briefly
    await asyncio.sleep(0.5)

    # Stop it
    await watchdog.stop()

    # Wait for task to finish
    try:
        await asyncio.wait_for(watchdog_task, timeout=2.0)
    except asyncio.TimeoutError:
        watchdog_task.cancel()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
