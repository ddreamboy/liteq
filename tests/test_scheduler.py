"""Tests for scheduler functionality"""

import os
from datetime import datetime, timedelta

import pytest

from liteq import register_schedule, task
from liteq.db import get_conn, init_db
from liteq.scheduler import (
    Scheduler,
    calculate_next_run,
    disable_schedule,
    enable_schedule,
    list_schedules,
    parse_cron,
)

TEST_DB = "test_scheduler.db"


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
def scheduled_task():
    """Test scheduled task"""
    return "executed"


def test_parse_cron_valid():
    """Test parsing valid cron expressions"""
    # Every day at 9 AM
    result = parse_cron("0 9 * * *")
    assert result["minute"] == "0"
    assert result["hour"] == "9"
    assert result["day"] == "*"

    # Every 5 minutes
    result = parse_cron("*/5 * * * *")
    assert result["minute"] == "*/5"


def test_parse_cron_invalid():
    """Test parsing invalid cron expressions"""
    with pytest.raises(ValueError):
        parse_cron("invalid")

    with pytest.raises(ValueError):
        parse_cron("0 9 *")  # Too few fields


def test_calculate_next_run_interval():
    """Test calculating next run for interval patterns"""
    # Every 5 minutes
    now = datetime.now()
    next_run = calculate_next_run("*/5 * * * *", now)

    assert next_run > now
    # Should be around 5 minutes from now (with rounding)
    diff = (next_run - now).total_seconds()
    assert 0 < diff <= 300  # Up to 5 minutes


def test_calculate_next_run_specific_time():
    """Test calculating next run for specific time"""
    # Daily at 9 AM
    now = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    next_run = calculate_next_run("0 9 * * *", now)

    assert next_run.hour == 9
    assert next_run.minute == 0
    assert next_run > now


def test_register_schedule():
    """Test registering a schedule"""
    schedule_id = register_schedule(scheduled_task, "0 9 * * *")

    assert schedule_id is not None
    assert schedule_id > 0

    # Check in database
    with get_conn() as conn:
        schedule = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()

        assert schedule is not None
        assert schedule["task_name"] == "scheduled_task"
        assert schedule["cron_expr"] == "0 9 * * *"
        assert schedule["enabled"] == 1
        assert schedule["next_run"] is not None


def test_register_schedule_with_args():
    """Test registering schedule with task arguments"""

    @task()
    def task_with_args(msg: str, count: int):
        return f"{msg} x {count}"

    schedule_id = register_schedule(task_with_args, "*/5 * * * *", queue="scheduled", msg="Hello", count=5)

    with get_conn() as conn:
        schedule = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()

        assert schedule["queue"] == "scheduled"
        assert "Hello" in schedule["payload"]
        assert "5" in schedule["payload"]


def test_list_schedules():
    """Test listing all schedules"""
    # Register multiple schedules
    schedule_id_1 = register_schedule(scheduled_task, "0 9 * * *")
    schedule_id_2 = register_schedule(scheduled_task, "*/5 * * * *")

    schedules = list_schedules()

    assert len(schedules) >= 2
    schedule_ids = [s["id"] for s in schedules]
    assert schedule_id_1 in schedule_ids
    assert schedule_id_2 in schedule_ids


def test_disable_enable_schedule():
    """Test disabling and enabling schedules"""
    schedule_id = register_schedule(scheduled_task, "0 9 * * *")

    # Initially enabled
    with get_conn() as conn:
        schedule = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
        assert schedule["enabled"] == 1

    # Disable
    disable_schedule(schedule_id)
    with get_conn() as conn:
        schedule = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
        assert schedule["enabled"] == 0

    # Enable
    enable_schedule(schedule_id)
    with get_conn() as conn:
        schedule = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
        assert schedule["enabled"] == 1


def test_scheduler_process_schedules():
    """Test scheduler processing due schedules"""
    # Register a schedule that's due now
    schedule_id = register_schedule(scheduled_task, "*/5 * * * *")

    # Force schedule to be due
    past_time = (datetime.now() - timedelta(minutes=10)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE schedules SET next_run = ? WHERE id = ?", (past_time, schedule_id))

    # Create scheduler and process once
    scheduler = Scheduler(check_interval=1)
    scheduler._process_schedules()

    # Check that task was enqueued
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE name = 'scheduled_task' ORDER BY id DESC LIMIT 1").fetchone()

        assert task is not None
        assert task["status"] == "pending"
        assert task["priority"] == 5  # Scheduled tasks have priority 5

        # Check that schedule was updated
        schedule = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        assert schedule["last_run"] is not None
        assert schedule["next_run"] > datetime.now().isoformat()


def test_scheduler_skip_disabled():
    """Test that scheduler skips disabled schedules"""
    # Clear any existing tasks first
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE name = 'scheduled_task'")

    schedule_id = register_schedule(scheduled_task, "*/5 * * * *")

    # Disable schedule
    disable_schedule(schedule_id)

    # Force to be due
    past_time = (datetime.now() - timedelta(minutes=10)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE schedules SET next_run = ? WHERE id = ?", (past_time, schedule_id))

    # Process schedules
    scheduler = Scheduler(check_interval=1)
    scheduler._process_schedules()

    # No NEW task should be enqueued
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE name = 'scheduled_task'").fetchone()
        assert task is None


def test_scheduler_initialization():
    """Test scheduler initialization"""
    scheduler = Scheduler(check_interval=30)

    assert scheduler.check_interval == 30
    assert scheduler.running is False
