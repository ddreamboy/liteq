import asyncio
import logging
import random
import time

from liteq import task
from liteq.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@task(queue="emails", max_retries=3)
def send_email(email: str, subject: str):
    logging.info(f"Sending email to {email}: {subject}")
    time.sleep(random.uniform(1, 3))
    if random.random() < 0.1:
        raise ValueError(f"Failed to send email to {email}")
    return f"Email sent to {email}"


@task(queue="processing", max_retries=1)
async def process_data(data_id: int):
    logging.info(f"Processing data {data_id}")
    await asyncio.sleep(random.uniform(2, 5))
    if random.random() < 0.15:
        raise RuntimeError(f"Failed to process data {data_id}")
    return f"Data {data_id} processed successfully"


@task(queue="notifications", max_retries=2)
def send_notification(user_id: int, message: str):
    logging.info(f"Notification to user {user_id}: {message}")
    time.sleep(random.uniform(0.5, 1.5))
    return f"Notification sent to user {user_id}"


async def generate_continuous_tasks():
    """Generate tasks continuously"""
    task_counter = 0

    logging.info("Starting task generation...")

    try:
        while True:
            num_tasks = random.randint(3, 5)

            for _ in range(num_tasks):
                task_type = random.choice(["email", "data", "notification"])

                if task_type == "email":
                    send_email.delay(
                        email=f"user{task_counter}@example.com",
                        subject=f"Test Email {task_counter}",
                    )
                elif task_type == "data":
                    process_data.delay(data_id=task_counter)
                else:
                    send_notification.delay(
                        user_id=task_counter,
                        message=f"Hello from task {task_counter}",
                    )

                task_counter += 1

            logging.info(f"Generated {num_tasks} tasks (total: {task_counter})")

            await asyncio.sleep(random.uniform(5, 10))

    except KeyboardInterrupt:
        logging.info(f"\nStopped. Total tasks generated: {task_counter}")


if __name__ == "__main__":
    # Initialize database
    init_db()

    logging.info("""
╔══════════════════════════════════════════════════════════════╗
║         LiteQ Demo Monitor                                   ║
║                                                              ║
║  This demo generates random tasks continuously               ║
║                                                              ║
║  To use:                                                     ║
║  1. Run workers: liteq worker --app examples/demo_monitor.py --queues emails,processing,notifications --concurrency 4
║  2. Run this script to generate tasks                        ║
║  3. Open monitor: liteq monitor (in another terminal)        ║
║  4. Open http://127.0.0.1:5151 in browser                    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    input("Press Enter to start generating tasks...")

    asyncio.run(generate_continuous_tasks())
    start_monitor_thread()

    await asyncio.sleep(2)

    generator_task = asyncio.create_task(generate_continuous_tasks())

    try:
        await run_workers()
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        generator_task.cancel()
        await asyncio.sleep(1)
        print("Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
