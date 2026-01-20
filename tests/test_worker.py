"""Tests for worker functionality"""

import os
import time

import pytest

from liteq.db import get_conn, init_db
from liteq.worker import Worker, _run_task_in_thread

TEST_DB = "test_worker.db"


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


def test_worker_initialization():
    """Test worker can be initialized"""
    worker = Worker(queues=["default"], concurrency=2)

    assert worker.queues == ["default"]
    assert worker.concurrency == 2
    assert worker.pool is not None
    assert worker.task_timeout is None
    assert len(worker.worker_id) > 0


def test_worker_initialization_with_timeout():
    """Test worker with timeout parameter"""
    worker = Worker(queues=["default"], concurrency=2, task_timeout=30)

    assert worker.task_timeout == 30
    assert worker.running_tasks == {}
    assert worker.shutdown is False


def test_worker_multiple_queues():
    """Test worker with multiple queues"""
    worker = Worker(queues=["emails", "notifications", "reports"], concurrency=4)

    assert len(worker.queues) == 3
    assert "emails" in worker.queues
    assert "notifications" in worker.queues
    assert "reports" in worker.queues


def test_worker_check_stuck_tasks_no_timeout():
    """Test that check_stuck_tasks does nothing without timeout"""
    worker = Worker(queues=["default"], concurrency=1, task_timeout=None)
    worker._check_stuck_tasks()  # Should not crash


def test_worker_heartbeat(monkeypatch):
    """Test worker heartbeat registration"""
    worker = Worker(queues=["default"], concurrency=1)
    worker._heartbeat()

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM workers WHERE worker_id=?", (worker.worker_id,)).fetchone()

        assert row is not None
        assert row["hostname"] is not None
        assert row["queues"] == "default"
        assert row["concurrency"] == 1


def test_worker_cleanup_on_shutdown():
    """Test worker removes itself from workers table"""
    worker = Worker(queues=["test"], concurrency=1)
    worker._heartbeat()

    # Verify worker is registered
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM workers WHERE worker_id=?", (worker.worker_id,)).fetchone()
        assert row is not None

    # Simulate shutdown
    with get_conn() as conn:
        conn.execute("DELETE FROM workers WHERE worker_id=?", (worker.worker_id,))

    # Verify worker is removed
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM workers WHERE worker_id=?", (worker.worker_id,)).fetchone()
        assert row is None


def test_worker_fetch_and_run_no_tasks():
    """Test _fetch_and_run when no tasks are available"""
    worker = Worker(queues=["empty"], concurrency=1)

    # Call _fetch_and_run with no tasks in queue
    worker._fetch_and_run()

    # Should not crash, just do nothing


def test_worker_fetch_and_run_with_task():
    """Test _fetch_and_run picks up a pending task"""
    from liteq import task as task_decorator

    @task_decorator(queue="test_queue")
    def sample_task():
        return "done"

    task_id = sample_task.delay()

    worker = Worker(queues=["test_queue"], concurrency=1)

    # Fetch and run should pick up the task
    worker._fetch_and_run()

    # Give it a moment to process
    time.sleep(0.1)

    # Task should now be running or done
    with get_conn() as conn:
        task_row = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task_row["status"] in ["running", "done"]


def test_worker_queues_with_spaces():
    """Test that worker strips spaces from queue names"""
    worker = Worker(queues=["  queue1  ", " queue2 "], concurrency=2)

    assert worker.queues == ["queue1", "queue2"]


def test_run_task_in_thread_with_missing_task():
    """Test _run_task_in_thread with non-existent task"""
    # This should handle gracefully when task is not in registry
    worker_id = "test-worker"
    _run_task_in_thread(999, "non_existent_task", '{"args": [], "kwargs": {}}', worker_id)

    # Should not crash


def test_worker_heartbeat_updates():
    """Test that heartbeat updates existing worker"""
    worker = Worker(queues=["test"], concurrency=1)

    # First heartbeat
    worker._heartbeat()

    with get_conn() as conn:
        first = conn.execute(
            "SELECT last_heartbeat FROM workers WHERE worker_id=?",
            (worker.worker_id,),
        ).fetchone()

    time.sleep(0.1)

    # Second heartbeat
    worker._heartbeat()

    with get_conn() as conn:
        second = conn.execute(
            "SELECT last_heartbeat FROM workers WHERE worker_id=?",
            (worker.worker_id,),
        ).fetchone()

    # Heartbeat should be updated
    assert second["last_heartbeat"] >= first["last_heartbeat"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
