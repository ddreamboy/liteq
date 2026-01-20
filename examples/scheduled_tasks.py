"""
Scheduled tasks example for LiteQ

This example shows how to use cron-like scheduling.

Run this example:
1. python examples/scheduled_tasks.py  # Register schedules
2. liteq scheduler --app examples/scheduled_tasks.py  # Run scheduler
3. liteq worker --app examples/scheduled_tasks.py  # Run worker
"""

import time
from datetime import datetime

from liteq import register_schedule, task
from liteq.db import init_db


@task(queue="scheduled")
def daily_backup():
    """Run daily backup at 2 AM"""
    print(f"[{datetime.now()}] Running daily backup...")
    time.sleep(2)
    print("Backup complete!")
    return {"status": "success", "timestamp": datetime.now().isoformat()}


@task(queue="scheduled")
def hourly_cleanup():
    """Run cleanup every hour"""
    print(f"[{datetime.now()}] Running hourly cleanup...")
    time.sleep(1)
    print("Cleanup complete!")
    return {"status": "success"}


@task(queue="scheduled")
def frequent_check():
    """Run every 5 minutes"""
    print(f"[{datetime.now()}] Running frequent check...")
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@task(queue="reports")
def generate_weekly_report(report_type: str):
    """Generate weekly report"""
    print(f"[{datetime.now()}] Generating {report_type} weekly report...")
    time.sleep(3)
    print(f"Weekly {report_type} report generated!")
    return {"report_type": report_type, "status": "generated"}


if __name__ == "__main__":
    # Initialize database
    init_db()

    print("Registering scheduled tasks...")

    # Register schedules

    # Daily backup at 2:00 AM
    schedule_id_1 = register_schedule(
        daily_backup,
        cron_expr="0 2 * * *",  # Every day at 2:00 AM
        queue="scheduled",
    )
    print(f"✓ Registered daily_backup (ID: {schedule_id_1})")

    # Cleanup every hour
    schedule_id_2 = register_schedule(
        hourly_cleanup,
        cron_expr="0 * * * *",  # Every hour
        queue="scheduled",
    )
    print(f"✓ Registered hourly_cleanup (ID: {schedule_id_2})")

    # Check every 5 minutes
    schedule_id_3 = register_schedule(
        frequent_check,
        cron_expr="*/5 * * * *",  # Every 5 minutes
        queue="scheduled",
    )
    print(f"✓ Registered frequent_check (ID: {schedule_id_3})")

    # Weekly report on Mondays at 9 AM
    schedule_id_4 = register_schedule(
        generate_weekly_report,
        cron_expr="0 9 * * 1",  # Every Monday at 9:00 AM
        queue="reports",
        report_type="sales",
    )
    print(f"✓ Registered weekly sales report (ID: {schedule_id_4})")

    print("\n" + "=" * 60)
    print("Schedules registered successfully!")
    print("=" * 60)
    print("\nTo run the scheduler:")
    print("  liteq scheduler --app examples/scheduled_tasks.py")
    print("\nTo process scheduled tasks:")
    print("  liteq worker --app examples/scheduled_tasks.py")
    print("\nTo view dashboard:")
    print("  liteq monitor")
    print("  Then visit: http://localhost:5151")
