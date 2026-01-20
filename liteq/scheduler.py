"""Cron-like scheduling for LiteQ tasks"""

import json
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from .db import get_conn, init_db


def parse_cron(cron_expr: str) -> dict:
    """
    Parse cron expression (simplified version).

    Format: "minute hour day month weekday"
    Example: "0 9 * * *" = every day at 9:00 AM
    Example: "*/5 * * * *" = every 5 minutes
    Example: "0 */2 * * *" = every 2 hours

    Special values:
    - * = any value
    - */N = every N units
    - N = specific value
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}. Expected 5 fields.")

    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "weekday": parts[4],
    }


def calculate_next_run(cron_expr: str, from_time: Optional[datetime] = None) -> datetime:
    """Calculate next run time based on cron expression"""
    if from_time is None:
        from_time = datetime.now()

    parsed = parse_cron(cron_expr)

    # Simple implementation for common patterns
    # For */N patterns
    if parsed["minute"].startswith("*/"):
        interval = int(parsed["minute"][2:])
        next_run = from_time + timedelta(minutes=interval)
        # Round to the interval
        next_run = next_run.replace(second=0, microsecond=0)
        return next_run

    # For specific time patterns like "0 9 * * *"
    if parsed["minute"].isdigit() and parsed["hour"].isdigit():
        minute = int(parsed["minute"])
        hour = int(parsed["hour"])

        next_run = from_time.replace(minute=minute, hour=hour, second=0, microsecond=0)

        # If time has passed today, schedule for tomorrow
        if next_run <= from_time:
            next_run += timedelta(days=1)

        return next_run

    # Default: run every hour
    return from_time + timedelta(hours=1)


def register_schedule(
    task_func: Callable, cron_expr: str, queue: str = "default", enabled: bool = True, *args, **kwargs
) -> int:
    """
    Register a task to run on a schedule.

    Args:
        task_func: Task function (decorated with @task)
        cron_expr: Cron expression (e.g., "0 9 * * *" for daily at 9 AM)
        queue: Queue name
        enabled: Whether schedule is active
        *args, **kwargs: Arguments to pass to task

    Returns:
        Schedule ID

    Example:
        @task()
        def daily_report():
            generate_report()

        # Run every day at 9 AM
        register_schedule(daily_report, "0 9 * * *")

        # Run every 5 minutes
        register_schedule(daily_report, "*/5 * * * *")
    """
    if hasattr(task_func, "_task_proxy"):
        task_name = task_func._task_proxy.name
    elif hasattr(task_func, "__name__"):
        task_name = task_func.__name__
    else:
        raise ValueError("task_func must be a function or task")

    payload = json.dumps({"args": args, "kwargs": kwargs})
    next_run = calculate_next_run(cron_expr)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO schedules (task_name, cron_expr, payload, queue, enabled, next_run)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_name, cron_expr, payload, queue, 1 if enabled else 0, next_run.isoformat()),
        )
        return cursor.lastrowid


class Scheduler:
    """
    Background scheduler that runs scheduled tasks.

    Usage:
        scheduler = Scheduler()
        scheduler.run()
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False

    def run(self):
        """Run scheduler loop"""
        init_db()
        print(f"[*] LiteQ Scheduler started (checking every {self.check_interval}s)")
        self.running = True

        try:
            while self.running:
                self._process_schedules()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n[*] Scheduler stopped")
            self.running = False

    def _process_schedules(self):
        """Check and enqueue scheduled tasks"""
        now = datetime.now()

        with get_conn() as conn:
            schedules = conn.execute(
                """
                SELECT * FROM schedules 
                WHERE enabled = 1 
                AND (next_run IS NULL OR next_run <= ?)
                """,
                (now.isoformat(),),
            ).fetchall()

            for schedule in schedules:
                schedule_id = schedule["id"]
                task_name = schedule["task_name"]
                cron_expr = schedule["cron_expr"]
                payload = schedule["payload"]
                queue = schedule["queue"]

                # Enqueue task
                try:
                    conn.execute(
                        """
                        INSERT INTO tasks (name, payload, queue, status, priority)
                        VALUES (?, ?, ?, 'pending', 5)
                        """,
                        (task_name, payload, queue),
                    )

                    # Update schedule
                    next_run = calculate_next_run(cron_expr, now)
                    conn.execute(
                        """
                        UPDATE schedules 
                        SET last_run = ?, next_run = ?
                        WHERE id = ?
                        """,
                        (now.isoformat(), next_run.isoformat(), schedule_id),
                    )

                    print(f"[+] Scheduled task '{task_name}' (next run: {next_run})")

                except Exception as e:
                    print(f"[!] Error scheduling task '{task_name}': {e}")


def list_schedules():
    """List all registered schedules"""
    with get_conn() as conn:
        schedules = conn.execute("SELECT * FROM schedules ORDER BY id").fetchall()
        return [dict(s) for s in schedules]


def disable_schedule(schedule_id: int):
    """Disable a schedule"""
    with get_conn() as conn:
        conn.execute("UPDATE schedules SET enabled = 0 WHERE id = ?", (schedule_id,))


def enable_schedule(schedule_id: int):
    """Enable a schedule"""
    with get_conn() as conn:
        conn.execute("UPDATE schedules SET enabled = 1 WHERE id = ?", (schedule_id,))
