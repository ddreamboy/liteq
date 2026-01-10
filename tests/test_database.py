"""Tests for database operations"""

import os

import pytest

from liteq.db import get_conn, init_db

TEST_DB = "test_db.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup test database"""
    monkeypatch.setenv("LITEQ_DB", TEST_DB)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    yield

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_db_initialization():
    """Test database initialization creates tables"""
    init_db()

    with get_conn() as conn:
        # Check tasks table
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
        )
        result = cursor.fetchone()
        assert result is not None

        # Check all columns exist
        sql = result[0]
        assert "id INTEGER PRIMARY KEY" in sql
        assert "name TEXT NOT NULL" in sql
        assert "payload TEXT NOT NULL" in sql
        assert "queue TEXT NOT NULL" in sql
        assert "status TEXT DEFAULT 'pending'" in sql
        assert "priority INTEGER DEFAULT 0" in sql
        assert "max_retries INTEGER DEFAULT 3" in sql


def test_db_workers_table():
    """Test workers table structure"""
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='workers'"
        )
        result = cursor.fetchone()
        assert result is not None

        sql = result[0]
        assert "worker_id TEXT PRIMARY KEY" in sql
        assert "hostname TEXT" in sql
        assert "queues TEXT" in sql
        assert "concurrency INTEGER" in sql


def test_db_index_created():
    """Test that index is created"""
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_fetch'"
        )
        assert cursor.fetchone() is not None


def test_db_connection_settings():
    """Test database connection settings"""
    init_db()

    with get_conn() as conn:
        # Check WAL mode
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal == "wal"

        # Check synchronous mode
        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        assert sync == 1  # NORMAL


def test_db_insert_task():
    """Test inserting a task"""
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (name, payload, queue) VALUES (?, ?, ?)",
            ("test_task", '{"args": [], "kwargs": {}}', "default"),
        )
        task_id = cursor.lastrowid

        # Fetch the task
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row["name"] == "test_task"
        assert row["status"] == "pending"
        assert row["priority"] == 0


def test_db_update_task_status():
    """Test updating task status"""
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (name, payload, queue) VALUES (?, ?, ?)",
            ("test_task", "{}", "default"),
        )
        task_id = cursor.lastrowid

        # Update status
        conn.execute(
            "UPDATE tasks SET status=? WHERE id=?",
            ("running", task_id),
        )

        # Check update
        row = conn.execute(
            "SELECT status FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        assert row["status"] == "running"


def test_db_register_worker():
    """Test registering a worker"""
    import uuid

    worker_id = f"worker-{uuid.uuid4().hex[:8]}"

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO workers (worker_id, hostname, queues, concurrency)
               VALUES (?, ?, ?, ?)""",
            (worker_id, "localhost", "default", 4),
        )

        row = conn.execute(
            "SELECT * FROM workers WHERE worker_id=?", (worker_id,)
        ).fetchone()

        assert row["hostname"] == "localhost"
        assert row["queues"] == "default"
        assert row["concurrency"] == 4


def test_db_query_pending_tasks():
    """Test querying pending tasks"""
    # Note: this test needs isolation, so we use a transaction
    with get_conn() as conn:
        # Count existing pending tasks
        existing = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE status='pending'"
        ).fetchone()["cnt"]

        # Insert some tasks
        inserted_ids = []
        for i in range(5):
            cursor = conn.execute(
                "INSERT INTO tasks (name, payload, queue, priority) VALUES (?, ?, ?, ?)",
                (f"test_query_task_{i}", "{}", "test_query", i * 10),
            )
            inserted_ids.append(cursor.lastrowid)

        # Query only our pending tasks
        placeholders = ",".join(["?"] * len(inserted_ids))
        rows = conn.execute(
            f"""SELECT * FROM tasks 
               WHERE id IN ({placeholders}) AND status='pending' 
               ORDER BY priority DESC""",
            inserted_ids,
        ).fetchall()

        assert len(rows) == 5
        # Highest priority first
        assert rows[0]["priority"] == 40


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
