import asyncio
import logging
from liteq import task, QueueManager, enqueue, enqueue_many

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
    import time

    time.sleep(0.5)
    logging.info(f"SMS sent to {phone}")


@task(queue="cleanup", max_retries=1)
async def cleanup_temp_files(older_than_days: int):
    """Cleanup task (simulated)"""
    logging.info(f"Cleaning up temp files older than {older_than_days} days")
    await asyncio.sleep(1.5)
    logging.info("Cleanup completed")


async def main():
    manager = QueueManager(db_path="multi_queue_example.db")
    manager.initialize()

    # Worker 1: handles emails and notifications
    manager.add_worker("email-worker", queues=["emails", "notifications"])

    # Worker 2: dedicated to reports (CPU intensive)
    manager.add_worker("report-worker", queues=["reports"])

    # Worker 3: handles cleanup and low-priority tasks
    manager.add_worker("cleanup-worker", queues=["cleanup"])

    # Enqueue tasks to different queues
    logging.info("Enqueueing tasks...")

    # Email tasks
    enqueue(
        "send_email",
        {
            "to": "user@example.com",
            "subject": "Welcome!",
            "body": "Thanks for signing up",
        },
        queue="emails",
        priority=10,
    )

    enqueue(
        "send_email",
        {"to": "admin@example.com", "subject": "Alert", "body": "System update"},
        queue="emails",
        priority=100,
    )  # Higher priority

    # Report tasks
    enqueue(
        "generate_report",
        {"report_id": 123, "report_type": "sales"},
        queue="reports",
        priority=5,
    )

    enqueue(
        "generate_report",
        {"report_id": 124, "report_type": "analytics"},
        queue="reports",
        priority=3,
    )

    # Notification tasks
    enqueue(
        "send_sms",
        {"phone": "+1234567890", "message": "Your code is 1234"},
        queue="notifications",
    )

    # Cleanup task (delayed by 5 seconds)
    enqueue("cleanup_temp_files", {"older_than_days": 30}, queue="cleanup", delay=5)

    # Batch enqueue
    email_batch = [
        {
            "task_name": "send_email",
            "payload": {"to": f"user{i}@example.com", "subject": "Newsletter"},
            "queue": "emails",
            "priority": 1,
        }
        for i in range(1, 6)
    ]
    enqueue_many(email_batch)

    logging.info(f"Enqueued {len(email_batch) + 6} tasks")

    # Show stats
    from liteq import get_queue_stats

    stats = get_queue_stats()
    logging.info("Queue Statistics:")
    for stat in stats:
        logging.info(f"   {stat['queue']}: {stat['count']} {stat['status']} tasks")

    # Start processing (press Ctrl+C to stop)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
