import pytest
import asyncio
import os
from liteq import (
    task,
    QueueManager,
    enqueue,
    enqueue_many,
    get_queue_stats,
    get_task_by_id,
    get_pending_count,
)

# Use a test database
TEST_DB = "test_liteq.db"


@pytest.fixture(autouse=True)
def cleanup_db():
    """Remove test database before and after each test"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@task(queue="test")
async def my_async_task(num: int):
    """Test async task"""
    await asyncio.sleep(0.1)
    return num * 2


@task(queue="test")
def my_sync_task(num: int):
    """Test sync task"""
    return num * 3


@pytest.mark.asyncio
async def test_enqueue_and_process():
    """Test basic enqueue and process"""
    manager = QueueManager(db_path=TEST_DB)
    manager.initialize()

    # Enqueue a task
    task_id = enqueue("my_async_task", {"num": 5}, queue="test")
    assert task_id > 0

    # Check task exists
    task = get_task_by_id(task_id)
    assert task is not None
    assert task["name"] == "my_async_task"
    assert task["status"] == "pending"


@pytest.mark.asyncio
async def test_multiple_queues():
    """Test multiple queues"""
    manager = QueueManager(db_path=TEST_DB)
    manager.initialize()

    # Enqueue to different queues
    id1 = enqueue("my_async_task", {"num": 1}, queue="queue1")
    id2 = enqueue("my_async_task", {"num": 2}, queue="queue2")

    task1 = get_task_by_id(id1)
    task2 = get_task_by_id(id2)

    assert task1["queue"] == "queue1"
    assert task2["queue"] == "queue2"


@pytest.mark.asyncio
async def test_priorities():
    """Test task priorities"""
    manager = QueueManager(db_path=TEST_DB)
    manager.initialize()

    # Enqueue with different priorities
    low = enqueue("my_async_task", {"num": 1}, priority=1, queue="test")
    high = enqueue("my_async_task", {"num": 2}, priority=100, queue="test")

    task_low = get_task_by_id(low)
    task_high = get_task_by_id(high)

    assert task_low["priority"] == 1
    assert task_high["priority"] == 100


@pytest.mark.asyncio
async def test_batch_enqueue():
    """Test batch enqueueing"""
    manager = QueueManager(db_path=TEST_DB)
    manager.initialize()

    tasks = [
        {"task_name": "my_async_task", "payload": {"num": i}, "queue": "test"} for i in range(10)
    ]

    task_ids = enqueue_many(tasks)
    assert len(task_ids) == 10

    pending = get_pending_count(queue="test")
    assert pending == 10


@pytest.mark.asyncio
async def test_queue_stats():
    """Test queue statistics"""
    manager = QueueManager(db_path=TEST_DB)
    manager.initialize()

    # Enqueue some tasks
    for i in range(5):
        enqueue("my_async_task", {"num": i}, queue="test")

    stats = get_queue_stats(queue="test")
    assert len(stats) > 0

    pending_stat = next((s for s in stats if s["status"] == "pending"), None)
    assert pending_stat is not None
    assert pending_stat["count"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
