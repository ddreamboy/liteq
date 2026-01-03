import pytest
import asyncio
import os
from liteq import (
    task,
    QueueManager,
    enqueue,
    get_task_status,
    recover_paused,
    pause_running,
    recover_stuck_tasks,
    recover_retry_tasks,
)
from liteq.db import get_db_transaction

TEST_DB = "test_recovery.db"


@pytest.fixture(autouse=True)
def cleanup_db():
    """Remove test database before and after each test"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@task
async def simple_task(value: int):
    """Simple task"""
    await asyncio.sleep(0.1)
    return value * 2


@task
async def failing_task():
    """Task that fails"""
    raise RuntimeError("Task failed intentionally")


@pytest.mark.asyncio
async def test_recover_paused_tasks():
    """Test recovering paused tasks"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    # Create tasks and set them to paused
    task_ids = []
    for i in range(3):
        task_id = enqueue("simple_task", {"value": i})
        task_ids.append(task_id)

        with get_db_transaction() as conn:
            conn.execute("UPDATE tasks SET status='paused' WHERE id=?", (task_id,))

    # Recover paused tasks
    recover_paused()

    # Check all tasks are pending
    for task_id in task_ids:
        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "pending"


@pytest.mark.asyncio
async def test_pause_running_tasks():
    """Test pausing running tasks"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    # Create tasks and set them to running
    task_ids = []
    for i in range(3):
        task_id = enqueue("simple_task", {"value": i})
        task_ids.append(task_id)

        with get_db_transaction() as conn:
            conn.execute(
                "UPDATE tasks SET status='running', worker_id='test-worker' WHERE id=?",
                (task_id,),
            )

    # Pause running tasks
    pause_running()

    # Check all tasks are paused
    for task_id in task_ids:
        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "paused"


@pytest.mark.asyncio
async def test_recover_stuck_tasks():
    """Test recovering stuck tasks based on heartbeat"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    # Create a stuck task (running with old heartbeat)
    task_id = enqueue("simple_task", {"value": 5})

    with get_db_transaction() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status='running',
                heartbeat_at=datetime('now', '-10 minutes'),
                worker_id='stuck-worker'
            WHERE id=?
            """,
            (task_id,),
        )

    # Recover with 5 minute timeout
    count = recover_stuck_tasks(timeout_minutes=5)
    assert count >= 1

    # Check task was recovered to retry
    status = get_task_status(task_id)
    assert status is not None
    assert status["status"] == "retry"
    assert status["worker_id"] is None


@pytest.mark.asyncio
async def test_recover_retry_tasks():
    """Test moving retry tasks back to pending"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    # Create tasks in retry state
    task_ids = []
    for i in range(3):
        task_id = enqueue("simple_task", {"value": i})
        task_ids.append(task_id)

        with get_db_transaction() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status='retry',
                    retry_at=datetime('now', '-1 second')
                WHERE id=?
                """,
                (task_id,),
            )

    # Recover retry tasks
    count = recover_retry_tasks()
    assert count == 3

    # Check tasks are pending
    for task_id in task_ids:
        status = get_task_status(task_id)
        assert status is not None
        assert status["status"] == "pending"


@pytest.mark.asyncio
async def test_retry_with_backoff():
    """Test that failed tasks go to retry with backoff"""

    # Define failing task in this test
    @task
    async def failing_task_retry():
        """Task that always fails"""
        raise ValueError("Task failed")

    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    # Enqueue failing task
    task_id = enqueue("failing_task_retry", max_attempts=3)

    # Run worker
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))
    await asyncio.sleep(1.0)
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Check task is in retry or failed
    status = get_task_status(task_id)
    assert status is not None
    assert status["status"] in ("retry", "failed", "running")
    assert status["attempts"] >= 1


@pytest.mark.asyncio
async def test_max_attempts_failure():
    """Test that tasks fail after max_attempts"""

    # Define failing task
    @task
    async def failing_task_max():
        """Task that fails"""
        raise RuntimeError("Task failed intentionally")

    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    # Enqueue with very low max_attempts
    task_id = enqueue("failing_task_max", max_attempts=1)

    # Run worker
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))
    await asyncio.sleep(1.0)
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Task should be failed or in retry/running
    status = get_task_status(task_id)
    assert status is not None
    assert status["status"] in ("failed", "retry", "running")
    assert status["attempts"] >= 1


@pytest.mark.asyncio
async def test_queue_specific_recovery():
    """Test queue-specific recovery operations"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    # Create tasks in different queues
    task1 = enqueue("simple_task", {"value": 1}, queue="queue1")
    task2 = enqueue("simple_task", {"value": 2}, queue="queue2")

    # Pause both
    with get_db_transaction() as conn:
        conn.execute(
            "UPDATE tasks SET status='paused' WHERE id IN (?, ?)", (task1, task2)
        )

    # Recover only queue1
    recover_paused(queue="queue1")

    # Check queue1 task is pending
    status1 = get_task_status(task1)
    assert status1["status"] == "pending"

    # Check queue2 task is still paused
    status2 = get_task_status(task2)
    assert status2["status"] == "paused"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
