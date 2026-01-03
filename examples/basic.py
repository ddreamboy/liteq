import asyncio
import logging
from liteq import task, QueueManager, enqueue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@task(max_retries=3)
async def hello(name: str):
    """Simple async task"""
    logging.info(f"Hello, {name}!")
    await asyncio.sleep(1)


@task(max_retries=2)
def greet_sync(name: str):
    """Simple sync task"""
    logging.info(f"Greetings, {name}!")
    import time

    time.sleep(0.5)


async def main():
    # Initialize manager
    manager = QueueManager(db_path="tasks.db")
    manager.initialize()

    # Add a worker
    manager.add_worker("worker-1", queues=["default"])

    # Enqueue some tasks
    enqueue("hello", {"name": "Alice"})
    enqueue("hello", {"name": "Bob"}, delay=2)
    enqueue("greet_sync", {"name": "Charlie"})

    # Start processing (press Ctrl+C to stop)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
