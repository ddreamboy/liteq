"""Tests for timeout functionality"""

import os
import time

import pytest

from liteq import task
from liteq.db import get_conn, init_db
from liteq.worker import Worker

TEST_DB = "test_timeout.db"


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
def quick_task():
    """Quick task that completes fast"""
    time.sleep(0.1)
    return "done"


@task()
def slow_task():
    """Slow task that takes time"""
    time.sleep(10)
    return "done"


@task()
def stuck_task():
    """Task that hangs forever"""
    while True:
        time.sleep(1)


def test_task_timeout_in_database():
    """Test that timeout is stored in database"""

    @task(timeout=30)
    def timed_task():
        return "ok"

    task_id = timed_task.delay()

    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task_row["timeout"] == 30


def test_worker_without_timeout():
    """Test worker initialization without timeout"""
    worker = Worker(queues=["default"], concurrency=2)

    assert worker.task_timeout is None
    worker._check_stuck_tasks()  # Should not crash


def test_worker_with_timeout():
    """Test worker initialization with timeout"""
    worker = Worker(queues=["default"], concurrency=2, task_timeout=5)

    assert worker.task_timeout == 5
    assert worker.running_tasks == {}


def test_worker_tracks_running_tasks():
    """Test that worker tracks running tasks"""
    worker = Worker(queues=["default"], concurrency=2, task_timeout=5)

    # Enqueue a quick task
    task_id = quick_task.delay()

    # Fetch and run
    worker._fetch_and_run()

    # Should be in running_tasks (check if there's any running task)
    assert len(worker.running_tasks) > 0

    # Wait for completion
    time.sleep(1)

    # Clean up completed by calling _fetch_and_run which cleans up
    worker._fetch_and_run()

    # Most tasks should be done now
    assert len(worker.running_tasks) <= 1


def test_worker_check_stuck_tasks():
    """Test that worker detects and handles stuck tasks"""
    worker = Worker(queues=["default"], concurrency=2, task_timeout=2)

    # Find next available task ID
    with get_conn() as conn:
        max_id = conn.execute("SELECT MAX(id) FROM tasks").fetchone()[0]
        fake_task_id = (max_id or 0) + 1

    from concurrent.futures import Future

    fake_future = Future()  # Create a real Future object
    old_time = time.time() - 10  # 10 seconds ago

    # Simulate task in database
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tasks (id, name, payload, queue, status) VALUES (?, ?, ?, ?, ?)",
            (fake_task_id, "test", "{}", "default", "running"),
        )

    # Add to running tasks with old timestamp
    worker.running_tasks[fake_task_id] = (fake_future, old_time)

    # Check stuck tasks
    worker._check_stuck_tasks()

    # Task should be removed from tracking
    assert fake_task_id not in worker.running_tasks

    # Task should be marked as failed in database
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (fake_task_id,)).fetchone()
        assert task["status"] == "failed"
        assert "timeout" in task["error"].lower()


def test_worker_respects_concurrency():
    """Test that worker respects concurrency limit"""
    worker = Worker(queues=["default"], concurrency=2, task_timeout=10)

    # Enqueue more tasks than concurrency
    for i in range(5):
        slow_task.delay()

    # Fetch tasks
    for _ in range(5):
        worker._fetch_and_run()

    # Should only have 2 running (concurrency limit)
    assert len(worker.running_tasks) <= 2


def test_task_started_at_timestamp():
    """Test that started_at timestamp is set when task starts"""
    from liteq.worker import _run_task_in_thread

    task_id = quick_task.delay()

    with get_conn() as conn:
        task_row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()

    _run_task_in_thread(task_row["id"], task_row["name"], task_row["payload"], "test-worker")

    time.sleep(0.5)

    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task["started_at"] is not None
        assert task["finished_at"] is not None
        assert task["status"] == "done"


def test_schedule_method():
    """Test scheduling a task for later execution"""
    from datetime import datetime, timedelta

    future_time = datetime.now() + timedelta(hours=1)
    task_id = quick_task.schedule(future_time)

    assert task_id is not None

    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task["status"] == "pending"
        # run_at should be in the future
        assert task["run_at"] > datetime.now().isoformat()
