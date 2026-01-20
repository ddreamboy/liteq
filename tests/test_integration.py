"""Integration tests for task execution"""

import asyncio
import os
import time

import pytest

from liteq import task
from liteq.db import get_conn, init_db
from liteq.worker import _run_task_in_thread

TEST_DB = "test_integration.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup test database"""
    monkeypatch.setenv("LITEQ_DB", TEST_DB)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    init_db()

    yield

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@task()
def multiply(a: int, b: int):
    """Simple sync task"""
    return a * b


@task()
async def async_add(a: int, b: int):
    """Simple async task"""
    await asyncio.sleep(0.01)
    return a + b


@task()
def failing_task():
    """Task that raises an error"""
    raise ValueError("This task always fails")


def test_sync_task_execution():
    """Test executing sync task"""
    task_id = multiply.delay(3, 7)

    # Get task details
    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task_row is not None

    # Execute task
    worker_id = "test-worker"
    _run_task_in_thread(task_row["id"], task_row["name"], task_row["payload"], worker_id)

    # Give it a moment to complete
    time.sleep(0.5)

    # Check result
    with get_conn() as conn:
        result = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert result["status"] == "done"
        assert "21" in result["result"]


def test_async_task_execution():
    """Test executing async task"""
    task_id = async_add.delay(10, 20)

    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()

    worker_id = "test-worker"
    _run_task_in_thread(task_row["id"], task_row["name"], task_row["payload"], worker_id)

    time.sleep(0.5)

    with get_conn() as conn:
        result = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert result["status"] == "done"
        assert "30" in result["result"]


def test_failing_task_execution():
    """Test that failing tasks are marked as failed"""
    task_id = failing_task.delay()

    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()

    worker_id = "test-worker"
    _run_task_in_thread(task_row["id"], task_row["name"], task_row["payload"], worker_id)

    time.sleep(0.5)

    with get_conn() as conn:
        result = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert result["status"] == "failed"
        assert "ValueError" in result["error"]

    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()

    worker_id = "test-worker"
    _run_task_in_thread(task_row["id"], task_row["name"], task_row["payload"], worker_id)

    time.sleep(0.5)

    with get_conn() as conn:
        result = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert result["status"] == "failed"
        assert "This task always fails" in result["error"]


def test_task_with_no_args():
    """Test task without arguments"""

    @task()
    def no_args_task():
        return "success"

    task_id = no_args_task.delay()

    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()

    worker_id = "test-worker"
    _run_task_in_thread(task_row["id"], task_row["name"], task_row["payload"], worker_id)

    time.sleep(0.5)

    with get_conn() as conn:
        result = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert result["status"] == "done"


def test_multiple_tasks_different_queues():
    """Test tasks in different queues"""

    @task(queue="queue1")
    def task1(x: int):
        return x

    @task(queue="queue2")
    def task2(x: int):
        return x * 2

    id1 = task1.delay(10)
    id2 = task2.delay(10)

    with get_conn() as conn:
        t1 = conn.execute("SELECT * FROM tasks WHERE id=?", (id1,)).fetchone()
        t2 = conn.execute("SELECT * FROM tasks WHERE id=?", (id2,)).fetchone()

        assert t1["queue"] == "queue1"
        assert t2["queue"] == "queue2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
