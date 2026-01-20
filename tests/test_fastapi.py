"""Tests for FastAPI integration"""

import os

import pytest

from liteq import task
from liteq.db import get_conn, init_db

TEST_DB = "test_fastapi.db"


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
def email_task(to: str, subject: str):
    """Mock email task"""
    return {"sent": True, "to": to, "subject": subject}


@task()
async def async_task(data: dict):
    """Mock async task"""
    return {"processed": True, "data": data}


def test_enqueue_task():
    """Test enqueue_task helper"""
    from liteq.fastapi import enqueue_task

    task_id = enqueue_task(email_task, "user@example.com", "Hello")

    assert task_id is not None
    assert task_id > 0

    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task is not None
        assert task["name"] == "email_task"


def test_enqueue_task_with_non_task():
    """Test that enqueue_task raises error for non-tasks"""
    from liteq.fastapi import enqueue_task

    def regular_function():
        return "ok"

    with pytest.raises(ValueError, match="not a LiteQ task"):
        enqueue_task(regular_function)


def test_liteq_background_tasks():
    """Test LiteQBackgroundTasks"""
    from liteq.fastapi import LiteQBackgroundTasks

    background = LiteQBackgroundTasks(queue="emails", priority=5)

    # Add task
    task_id = background.add_task(email_task, "user@example.com", "Test")

    assert task_id is not None
    assert task_id in background.tasks

    # Check in database
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task is not None
        # Task uses queue from decorator, not from LiteQBackgroundTasks
        assert task["queue"] == "default"


def test_liteq_background_tasks_multiple():
    """Test adding multiple tasks"""
    from liteq.fastapi import LiteQBackgroundTasks

    background = LiteQBackgroundTasks()

    # Add multiple tasks
    task_id_1 = background.add_task(email_task, "user1@example.com", "Test 1")
    task_id_2 = background.add_task(email_task, "user2@example.com", "Test 2")
    task_id_3 = background.add_task(async_task, {"key": "value"})

    assert len(background.tasks) == 3
    assert task_id_1 in background.tasks
    assert task_id_2 in background.tasks
    assert task_id_3 in background.tasks


def test_liteq_background_tasks_with_wrapped_task():
    """Test that LiteQBackgroundTasks works with wrapped tasks"""
    from liteq.fastapi import LiteQBackgroundTasks

    background = LiteQBackgroundTasks()

    # Both should work
    task_id_1 = background.add_task(email_task, "user@example.com", "Test")
    task_id_2 = background.add_task(email_task._task_proxy, "user2@example.com", "Test2")

    assert task_id_1 is not None
    assert task_id_2 is not None


def test_liteq_background_tasks_invalid_function():
    """Test that LiteQBackgroundTasks raises error for non-tasks"""
    from liteq.fastapi import LiteQBackgroundTasks

    background = LiteQBackgroundTasks()

    def regular_function():
        return "ok"

    with pytest.raises(ValueError, match="not a LiteQ task"):
        background.add_task(regular_function)


def test_fastapi_integration_example():
    """Test realistic FastAPI usage pattern"""
    from liteq.fastapi import LiteQBackgroundTasks

    # Simulate FastAPI endpoint
    def send_email_endpoint(to: str, subject: str):
        background = LiteQBackgroundTasks(queue="emails")
        task_id = background.add_task(email_task, to, subject)
        return {"message": "Email queued", "task_id": task_id}

    result = send_email_endpoint("user@example.com", "Welcome")

    assert "task_id" in result
    assert result["message"] == "Email queued"

    # Verify task is in database
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (result["task_id"],)).fetchone()
        assert task is not None
        # Task uses queue from decorator, not from LiteQBackgroundTasks
        assert task["queue"] == "default"
        assert task["status"] == "pending"
