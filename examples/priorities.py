import asyncio
import logging

from liteq import task
from liteq.db import get_conn, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@task(queue="tasks")
async def process_task(task_id: int, priority_level: int):
    """Process a task"""
    logging.info(f"Processing task {task_id} (priority: {priority_level})")
    await asyncio.sleep(0.5)
    logging.info(f"Completed task {task_id}")


if __name__ == "__main__":
    # Initialize database
    init_db()

    logging.info("Enqueueing tasks with different priorities...")
    logging.info("Tasks will be enqueued in order: 1, 2, 3, 4, 5")
    logging.info("Expected execution order: 2(100), 4(50), 5(10), 3(5), 1(1)\n")

    # Enqueue tasks with different priorities
    # Note: Higher priority value = executed first!

    # Low priority
    with get_conn() as conn:
        from liteq.db import enqueue_task

        task1_id = enqueue_task(
            conn,
            "process_task",
            {"task_id": 1, "priority_level": 1},
            queue="tasks",
            priority=1,
        )

        # VIP - highest priority
        task2_id = enqueue_task(
            conn,
            "process_task",
            {"task_id": 2, "priority_level": 100},
            queue="tasks",
            priority=100,
        )

        # Medium-low priority
        task3_id = enqueue_task(
            conn,
            "process_task",
            {"task_id": 3, "priority_level": 5},
            queue="tasks",
            priority=5,
        )

        # High priority
        task4_id = enqueue_task(
            conn,
            "process_task",
            {"task_id": 4, "priority_level": 50},
            queue="tasks",
            priority=50,
        )

        # Medium priority
        task5_id = enqueue_task(
            conn,
            "process_task",
            {"task_id": 5, "priority_level": 10},
            queue="tasks",
            priority=10,
        )

        conn.commit()

    logging.info(
        f"\nEnqueued tasks: {task1_id}, {task2_id}, {task3_id}, {task4_id}, {task5_id}"
    )
    logging.info("\nTo process these tasks, run:")
    logging.info("  liteq worker --app examples/priorities.py --queues tasks")

    # Uncomment to run worker programmatically:
    # from liteq.worker import Worker
    # worker = Worker(queues=["tasks"], concurrency=1)  # concurrency=1 to see order clearly
    # worker.run()
