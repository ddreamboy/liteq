import asyncio
import logging
import time

from liteq import task
from liteq.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@task(queue="emails", max_retries=3)
async def send_email(to: str, subject: str, body: str = ""):
    """Send an email (simulated)"""
    logging.info(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)
    logging.info(f"Email sent to {to}")


@task(queue="reports", max_retries=5)
async def generate_report(report_id: int, report_type: str):
    """Generate a report (simulated)"""
    logging.info(f"Generating {report_type} report #{report_id}")
    await asyncio.sleep(2)
    logging.info(f"Report #{report_id} generated")


@task(queue="notifications", max_retries=2)
def send_sms(phone: str, message: str):
    """Send SMS notification (simulated, sync)"""
    logging.info(f"SMS to {phone}: {message}")
    time.sleep(0.5)
    logging.info(f"SMS sent to {phone}")


@task(queue="cleanup", max_retries=1)
async def cleanup_temp_files(older_than_days: int):
    """Cleanup task (simulated)"""
    logging.info(f"Cleaning up temp files older than {older_than_days} days")
    await asyncio.sleep(1.5)
    logging.info("Cleanup completed")


if __name__ == "__main__":
    # Initialize database
    init_db()

    logging.info("Enqueueing tasks to different queues...")

    # Email tasks
    email1 = send_email.delay(
        to="user@example.com", subject="Welcome!", body="Thanks for signing up"
    )
    email2 = send_email.delay(
        to="admin@example.com", subject="Alert", body="System update"
    )
    email3 = send_email.delay(
        to="vip@example.com", subject="VIP Update", body="Exclusive content"
    )

    # Report tasks
    report1 = generate_report.delay(report_id=123, report_type="Sales")
    report2 = generate_report.delay(report_id=456, report_type="Analytics")

    # Notification tasks
    sms1 = send_sms.delay(phone="+1234567890", message="Your code is 1234")
    sms2 = send_sms.delay(phone="+9876543210", message="Order confirmed")

    # Cleanup task
    cleanup1 = cleanup_temp_files.delay(older_than_days=30)

    logging.info(f"\nEnqueued {9} tasks across 4 queues")
    logging.info(f"  - emails: {email1}, {email2}, {email3}")
    logging.info(f"  - reports: {report1}, {report2}")
    logging.info(f"  - notifications: {sms1}, {sms2}")
    logging.info(f"  - cleanup: {cleanup1}")

    # Show queue statistics
    from liteq.monitoring import get_queue_stats, list_queues

    queues = list_queues()
    stats = get_queue_stats()

    logging.info("\nQueue Statistics:")
    for stat in stats:
        logging.info(f"   {stat['queue']}: {stat['count']} {stat['status']} tasks")

    logging.info("\nTo process these tasks, run multiple workers:")
    logging.info(
        "  Terminal 1: liteq worker --app examples/multiple_queues.py --queues emails,notifications"
    )
    logging.info(
        "  Terminal 2: liteq worker --app examples/multiple_queues.py --queues reports"
    )
    logging.info(
        "  Terminal 3: liteq worker --app examples/multiple_queues.py --queues cleanup"
    )

    # Start processing (press Ctrl+C to stop)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
