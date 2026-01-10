import asyncio
import logging

from liteq import task
from liteq.db import init_db
from liteq.monitoring import get_queue_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
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

    logging.info(
        f"Sending campaign {campaign_id} to {user['name']} ({user['email']})"
    )
    await asyncio.sleep(0.3)  # Simulate email sending
    logging.info(f"Email sent to {user['name']}")
    return {"user_id": user_id, "campaign_id": campaign_id, "status": "sent"}


@task(queue="analytics", max_retries=2)
async def track_email_open(user_id: int, campaign_id: int):
    """Track email open event"""
    logging.info(f"Tracking email open: user={user_id}, campaign={campaign_id}")
    await asyncio.sleep(0.1)
    return {"event": "open", "user_id": user_id, "campaign_id": campaign_id}


@task(queue="analytics", max_retries=2)
async def track_email_click(user_id: int, campaign_id: int, link: str):
    """Track email link click"""
    logging.info(f"Tracking click: user={user_id}, link={link}")
    await asyncio.sleep(0.1)
    return {
        "event": "click",
        "user_id": user_id,
        "campaign_id": campaign_id,
        "link": link,
    }


@task(queue="reports", max_retries=5)
async def generate_campaign_report(campaign_id: int):
    """Generate campaign performance report"""
    logging.info(f"Generating report for campaign {campaign_id}")
    await asyncio.sleep(2)
    logging.info(f"Report generated for campaign {campaign_id}")
    return {"campaign_id": campaign_id, "status": "completed"}


def launch_campaign(campaign_id: int):
    """Launch an email campaign"""
    logging.info(f"Launching campaign {campaign_id}...")

    task_ids = []

    # Send emails to all users
    for user in USERS:
        task_id = send_campaign_email.delay(
            user_id=user["id"], campaign_id=campaign_id
        )
        task_ids.append(task_id)
        logging.info(f"Enqueued email for {user['name']}: {task_id}")

    # Schedule some tracking events
    track_email_open.delay(user_id=1, campaign_id=campaign_id)
    track_email_open.delay(user_id=3, campaign_id=campaign_id)
    track_email_click.delay(
        user_id=1, campaign_id=campaign_id, link="https://example.com/promo"
    )

    # Schedule report generation
    report_id = generate_campaign_report.delay(campaign_id=campaign_id)
    logging.info(f"Enqueued report generation: {report_id}")

    logging.info(f"\nCampaign {campaign_id} launched!")
    logging.info(f"Enqueued {len(task_ids)} emails + analytics + report")

    return task_ids


if __name__ == "__main__":
    # Initialize database
    init_db()

    # Launch campaign
    campaign_id = 2024
    task_ids = launch_campaign(campaign_id)

    # Show queue stats
    stats = get_queue_stats()
    logging.info("\nQueue Statistics:")
    for stat in stats:
        logging.info(f"   {stat['queue']}/{stat['status']}: {stat['count']}")

    logging.info("\nTo process campaign, run workers:")
    logging.info(
        "  Terminal 1: liteq worker --app examples/email_campaign.py --queues emails --concurrency 2"
    )
    logging.info(
        "  Terminal 2: liteq worker --app examples/email_campaign.py --queues analytics"
    )
    logging.info(
        "  Terminal 3: liteq worker --app examples/email_campaign.py --queues reports"
    )
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
