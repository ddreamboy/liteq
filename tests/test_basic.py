"""Basic tests for liteq"""

import os

import pytest

from liteq import task
from liteq.db import get_conn, init_db

TEST_DB = "test_liteq.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup test database"""
    monkeypatch.setenv("LITEQ_DB", TEST_DB)

    # Clean up before test
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # Initialize database
    init_db()

    yield

    # Clean up after test
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_task_decorator():
    """Test that task decorator works"""

    @task()
    def simple_task(x: int):
        return x * 2

    assert hasattr(simple_task, "delay")
    assert callable(simple_task.delay)


def test_task_enqueue():
    """Test enqueueing a task"""

    @task(queue="test")
    def add_numbers(a: int, b: int):
        return a + b

    # Enqueue task
    task_id = add_numbers.delay(5, 3)

    assert task_id is not None
    assert task_id > 0

    # Check task in database
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row is not None
        assert row["name"] == "add_numbers"
        assert row["queue"] == "test"
        assert row["status"] == "pending"


def test_task_with_custom_name():
    """Test task with custom name"""

    @task(name="custom_task_name")
    def my_func():
        return "result"

    task_id = my_func.delay()

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row["name"] == "custom_task_name"


def test_task_with_max_retries():
    """Test task with custom max_retries"""

    @task(max_retries=5)
    def retry_task():
        return "ok"

    task_id = retry_task.delay()

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row["max_retries"] == 5


def test_task_with_kwargs():
    """Test task with keyword arguments"""

    @task()
    def task_with_kwargs(name: str, age: int, city: str = "Unknown"):
        return f"{name}, {age}, {city}"

    task_id = task_with_kwargs.delay(name="Alice", age=30, city="NYC")

    assert task_id > 0

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert '"name": "Alice"' in row["payload"]
        assert '"age": 30' in row["payload"]


def test_multiple_tasks_same_queue():
    """Test multiple tasks in same queue"""
    # Use unique queue name to avoid interference from other tests
    import uuid

    queue_name = f"emails_{uuid.uuid4().hex[:8]}"

    @task(queue=queue_name)
    def send_email(to: str):
        return f"Email sent to {to}"

    task_ids = [
        send_email.delay(to="user1@example.com"),
        send_email.delay(to="user2@example.com"),
        send_email.delay(to="user3@example.com"),
    ]

    assert len(task_ids) == 3

    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE queue=?", (queue_name,)
        ).fetchone()["cnt"]
        assert count == 3


def test_database_initialization():
    """Test database schema"""
    with get_conn() as conn:
        # Check tasks table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        )
        assert cursor.fetchone() is not None

        # Check workers table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workers'"
        )
        assert cursor.fetchone() is not None

        # Check index exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_fetch'"
        )
        assert cursor.fetchone() is not None


def test_task_default_values():
    """Test task default values in database"""

    @task()
    def default_task():
        pass

    task_id = default_task.delay()

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row["queue"] == "default"
        assert row["status"] == "pending"
        assert row["priority"] == 0
        assert row["attempts"] == 0
        assert row["max_retries"] == 3


def test_async_task_registration():
    """Test that async tasks are registered"""
    from liteq.core import TASK_REGISTRY

    @task()
    async def async_task():
        return "async"

    # Check that task is registered by name
    assert "async_task" in TASK_REGISTRY
    # The registry stores the original function, not the wrapper
    assert callable(TASK_REGISTRY["async_task"])


def test_sync_task_registration():
    """Test that sync tasks are registered"""
    from liteq.core import TASK_REGISTRY

    @task()
    def sync_task():
        return "sync"

    # Check that task is registered by name
    assert "sync_task" in TASK_REGISTRY
    # The registry stores the original function, not the wrapper
    assert callable(TASK_REGISTRY["sync_task"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
