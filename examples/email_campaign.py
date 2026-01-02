import asyncio
import logging
from datetime import datetime
from liteq import task, QueueManager, enqueue, enqueue_many, get_queue_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Simulated database of users
USERS = [
    {"id": 1, "email": "alice@example.com", "name": "Alice", "tier": "premium"},
    {"id": 2, "email": "bob@example.com", "name": "Bob", "tier": "free"},
    {
        "id": 3,
        "email": "charlie@example.com",
        "name": "Charlie",
        "tier": "premium",
    },
    {"id": 4, "email": "diana@example.com", "name": "Diana", "tier": "free"},
    {"id": 5, "email": "eve@example.com", "name": "Eve", "tier": "enterprise"},
]


@task(queue="emails", max_retries=3)
async def send_campaign_email(user_id: int, campaign_id: int):
    """Send a campaign email to a user"""
    user = next((u for u in USERS if u["id"] == user_id), None)
    if not user:
        raise ValueError(f"User {user_id} not found")

    logging.info(f"Sending campaign {campaign_id} to {user['name']} ({user['email']})")
    await asyncio.sleep(0.3)  # Simulate email sending
    logging.info(f"Email sent to {user['name']}")


@task(queue="analytics", max_retries=2)
async def track_email_open(user_id: int, campaign_id: int):
    """Track email open event"""
    logging.info(f"Tracking email open: user={user_id}, campaign={campaign_id}")
    await asyncio.sleep(0.1)


@task(queue="analytics", max_retries=2)
async def track_email_click(user_id: int, campaign_id: int, link: str):
    """Track email link click"""
    logging.info(f"Tracking click: user={user_id}, link={link}")
    await asyncio.sleep(0.1)


@task(queue="reports", max_retries=5)
async def generate_campaign_report(campaign_id: int):
    """Generate campaign performance report"""
    logging.info(f"Generating report for campaign {campaign_id}")
    await asyncio.sleep(2)
    logging.info(f"Report generated for campaign {campaign_id}")


async def launch_campaign(campaign_id: int, priority_tier: dict):
    """Launch an email campaign"""
    logging.info(f"Launching campaign {campaign_id}...")

    # Prepare email tasks with priority based on user tier
    email_tasks = []
    for user in USERS:
        priority = priority_tier.get(user["tier"], 1)
        email_tasks.append(
            {
                "task_name": "send_campaign_email",
                "payload": {"user_id": user["id"], "campaign_id": campaign_id},
                "queue": "emails",
                "priority": priority,
            }
        )

    # Batch enqueue all emails
    task_ids = enqueue_many(email_tasks)
    logging.info(f"Enqueued {len(task_ids)} emails")

    # Schedule report generation (delayed by 10 seconds to wait for emails)
    enqueue(
        "generate_campaign_report",
        {"campaign_id": campaign_id},
        queue="reports",
        delay=10,
    )

    return task_ids


async def main():
    manager = QueueManager(db_path="campaign_example.db")
    manager.initialize()

    # Worker setup:
    # - 2 workers for emails (high throughput)
    # - 1 worker for analytics
    # - 1 worker for reports
    manager.add_worker("email-worker-1", queues=["emails"], poll_interval=0.5)
    manager.add_worker("email-worker-2", queues=["emails"], poll_interval=0.5)
    manager.add_worker("analytics-worker", queues=["analytics"])
    manager.add_worker("report-worker", queues=["reports"])

    # Define priority tiers
    priority_tier = {
        "enterprise": 100,  # Highest priority
        "premium": 50,
        "free": 10,
    }

    # Launch campaign
    await launch_campaign(campaign_id=2024, priority_tier=priority_tier)

    # Simulate some email interactions after 3 seconds
    async def simulate_interactions():
        await asyncio.sleep(3)
        logging.info("Simulating user interactions...")
        enqueue(
            "track_email_open",
            {"user_id": 1, "campaign_id": 2024},
            queue="analytics",
        )
        enqueue(
            "track_email_open",
            {"user_id": 3, "campaign_id": 2024},
            queue="analytics",
        )
        enqueue(
            "track_email_click",
            {
                "user_id": 1,
                "campaign_id": 2024,
                "link": "https://example.com/promo",
            },
            queue="analytics",
        )

    asyncio.create_task(simulate_interactions())

    # Show initial stats
    logging.info("Initial Queue Stats:")
    stats = get_queue_stats()
    for stat in stats:
        logging.info(f"   {stat['queue']}/{stat['status']}: {stat['count']}")

    # Start processing
    logging.info("Starting workers...")
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
