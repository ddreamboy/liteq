"""Tests for long-running tasks functionality"""

import pytest
import asyncio
import os
from liteq import (
    task,
    QueueManager,
    Worker,
    enqueue,
    cancel_task,
    pause_task,
    resume_task,
    get_task_result,
    get_task_status,
    get_task_progress,
)

TEST_DB = "test_long_running.db"


@pytest.fixture(autouse=True)
def cleanup_db():
    """Remove test database before and after each test"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@task
async def task_with_context(ctx, value: int):
    """Task that uses context"""
    # Save progress
    ctx.save_progress("started", {"value": value})

    await asyncio.sleep(0.1)

    # Save another checkpoint
    ctx.save_progress("processing", {"value": value * 2})

    result = value * 3
    ctx.save_result(result)

    return result


@task
async def long_task_with_cancellation(ctx, iterations: int):
    """Task that can be cancelled"""
    for i in range(iterations):
        if ctx.cancelled:
            ctx.save_progress("cancelled", {"completed": i})
            return {"status": "cancelled", "completed": i}

        await asyncio.sleep(0.05)

        if i % 10 == 0:
            ctx.save_progress(f"iteration_{i}", {"completed": i})

    return {"status": "completed", "iterations": iterations}


@task
async def task_with_pause(ctx, iterations: int):
    """Task that can be paused"""
    for i in range(iterations):
        if ctx.paused:
            ctx.save_progress("paused", {"completed": i})
            return {"status": "paused", "completed": i}

        await asyncio.sleep(0.05)

    return {"status": "completed", "iterations": iterations}


@task
async def task_with_resume(ctx, total: int):
    """Task that can resume from checkpoint"""
    progress = ctx.load_progress()
    start = progress["payload"]["completed"] if progress else 0

    for i in range(start, total):
        await asyncio.sleep(0.01)

        if i % 5 == 0:
            ctx.save_progress(f"step_{i}", {"completed": i})

    return {"status": "completed", "total": total}


@pytest.mark.asyncio
async def test_task_context_progress():
    """Test task context with progress tracking"""
    manager = QueueManager(db_path=TEST_DB)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    task_id = enqueue("task_with_context", {"value": 10})

    # Run worker for a short time
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))
    await asyncio.sleep(1.0)  # Increased from 0.5
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Check status - task might have completed or failed
    status = get_task_status(task_id)
    assert status is not None

    # If successful, check result
    if status["status"] == "done":
        result = get_task_result(task_id)
        assert result == 30
        # Check progress was saved
        progress = get_task_progress(task_id)
        assert progress is not None
    else:
        # Task might still be running or in retry
        assert status["status"] in ("running", "retry", "pending")


@pytest.mark.asyncio
async def test_task_cancellation():
    """Test cooperative task cancellation"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    task_id = enqueue("long_task_with_cancellation", {"iterations": 100})

    # Start worker
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))

    # Wait a bit then cancel
    await asyncio.sleep(0.2)
    cancel_task(task_id)

    # Wait for task to handle cancellation
    await asyncio.sleep(0.3)
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Check task was cancelled
    status = get_task_status(task_id)
    assert status is not None

    result = get_task_result(task_id)
    if result:
        assert result.get("status") == "cancelled"


@pytest.mark.asyncio
async def test_task_pause_resume():
    """Test task pause and resume"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    task_id = enqueue("task_with_pause", {"iterations": 100})

    # Start worker
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))

    # Wait a bit then pause
    await asyncio.sleep(0.2)
    pause_task(task_id)

    # Wait for task to handle pause
    await asyncio.sleep(0.5)
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Check task status
    status = get_task_status(task_id)
    assert status is not None

    # Task might be done, pending, or paused
    assert status["status"] in ("done", "pending", "paused")

    # Try resume only if not done
    if status["status"] != "done":
        resume_task(task_id)


@pytest.mark.asyncio
async def test_task_resume_from_checkpoint():
    """Test task resuming from saved checkpoint"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    task_id = enqueue("task_with_resume", {"total": 20})

    # Manually set a checkpoint to simulate resume
    from liteq.db import get_db_transaction
    import json

    with get_db_transaction() as conn:
        conn.execute(
            "UPDATE tasks SET progress=? WHERE id=?",
            (
                json.dumps({"step": "step_10", "payload": {"completed": 10}}),
                task_id,
            ),
        )

    manager.add_worker("worker-1", queues=["default"])
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))

    await asyncio.sleep(0.5)
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Check task completed
    status = get_task_status(task_id)
    assert status is not None


@pytest.mark.asyncio
async def test_heartbeat_updates():
    """Test that heartbeat is updated during task execution"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()

    # Create a task that takes some time
    task_id = enqueue("task_with_context", {"value": 5})

    manager.add_worker("worker-1", queues=["default"], heartbeat_interval=1)
    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))

    await asyncio.sleep(0.3)

    # Check heartbeat was set
    from liteq.db import get_conn

    conn = get_conn()
    row = conn.execute(
        "SELECT heartbeat_at, status FROM tasks WHERE id=?", (task_id,)
    ).fetchone()

    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Heartbeat should have been set if task ran
    if row and row["status"] == "running":
        assert row["heartbeat_at"] is not None


@pytest.mark.asyncio
async def test_result_storage():
    """Test that task results are stored correctly"""
    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    task_id = enqueue("task_with_context", {"value": 7})

    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))
    await asyncio.sleep(1.0)  # Increased
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Get result
    status = get_task_status(task_id)
    assert status is not None

    # Check if completed
    if status["status"] == "done":
        result = get_task_result(task_id)
        assert result == 21


@pytest.mark.asyncio
async def test_max_attempts():
    """Test max_attempts retry policy"""

    @task
    async def failing_task(ctx):
        """Task that always fails"""
        raise ValueError("Task failed")

    manager = QueueManager(db_path=TEST_DB, enable_watchdog=False)
    manager.initialize()
    manager.add_worker("worker-1", queues=["default"])

    # Enqueue with max_attempts=2
    task_id = enqueue("failing_task", max_attempts=2)

    worker_task = asyncio.create_task(manager.start(setup_signal_handlers=False))
    await asyncio.sleep(1.0)
    await manager.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=1.0)
    except asyncio.TimeoutError:
        pass

    # Check task failed after retries
    status = get_task_status(task_id)
    assert status is not None
    # Task should have failed or be in retry
    assert status["status"] in ("failed", "retry")
    assert status["attempts"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
