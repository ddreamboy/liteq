import asyncio
import logging
import time

from liteq import task
from liteq.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@task(max_retries=3)
async def hello(name: str):
    """Simple async task"""
    logging.info(f"Hello, {name}!")
    await asyncio.sleep(1)
    logging.info(f"Finished greeting {name}")


@task(max_retries=2)
def greet_sync(name: str):
    """Simple sync task"""
    logging.info(f"Greetings, {name}!")
    time.sleep(0.5)
    logging.info(f"Finished sync greeting for {name}")


if __name__ == "__main__":
    # Initialize database
    init_db()

    logging.info("Enqueueing tasks...")

    # Enqueue tasks using .delay()
    task1 = hello.delay(name="Alice")
    task2 = hello.delay(name="Bob")
    task3 = greet_sync.delay(name="Charlie")

    logging.info(f"Enqueued task IDs: {task1}, {task2}, {task3}")
    logging.info("\nTo process these tasks, run:")
    logging.info("  liteq worker --app examples/basic.py")
    logging.info("\nOr run worker programmatically (uncomment code below)")

    # Uncomment to run worker programmatically:
    # from liteq.worker import Worker
    # worker = Worker(queues=["default"], concurrency=2)
    # worker.run()
