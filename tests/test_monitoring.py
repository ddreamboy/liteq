"""Tests for monitoring functionality"""

import os
import uuid

import pytest

from liteq import task
from liteq.db import get_conn, init_db
from liteq.monitoring import (
    get_active_workers,
    get_failed_tasks,
    get_queue_stats,
    get_recent_tasks,
    list_queues,
)

TEST_DB = "test_monitoring.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup test database"""
    # Use unique DB per test to avoid conflicts
    db_name = f"test_monitoring_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("LITEQ_DB", db_name)

    if os.path.exists(db_name):
        os.remove(db_name)

    init_db()

    yield

    if os.path.exists(db_name):
        os.remove(db_name)


def test_get_queue_stats():
    """Test getting queue statistics"""

    @task(queue="emails")
    def send_email():
        pass

    send_email.delay()
    send_email.delay()

    stats = get_queue_stats()

    assert len(stats) > 0
    assert any(s["queue"] == "emails" for s in stats)


def test_get_recent_tasks():
    """Test getting recent tasks"""

    @task()
    def task1():
        pass

    task1.delay()
    task1.delay()

    tasks = get_recent_tasks(limit=10)

    assert len(tasks) >= 2


def test_list_queues():
    """Test listing unique queues"""

    @task(queue="queue1")
    def task1():
        pass

    @task(queue="queue2")
    def task2():
        pass

    task1.delay()
    task2.delay()

    queues = list_queues()

    assert "queue1" in queues
    assert "queue2" in queues


def test_get_failed_tasks():
    """Test getting failed tasks"""

    @task()
    def failed_task():
        pass

    task_id = failed_task.delay()

    # Mark task as failed
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status='failed', error='Test error' WHERE id=?",
            (task_id,),
        )

    failed = get_failed_tasks(limit=10)

    assert len(failed) >= 1
    assert any(t["status"] == "failed" for t in failed)


def test_get_active_workers():
    """Test getting active workers"""
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"

    # Register a worker
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO workers (worker_id, hostname, queues, concurrency, last_heartbeat)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (worker_id, "localhost", "default,emails", 4),
        )

    workers = get_active_workers()

    assert len(workers) >= 1
    worker = next((w for w in workers if w["worker_id"] == worker_id), None)
    assert worker is not None
    assert worker["queues"] == ["default", "emails"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
