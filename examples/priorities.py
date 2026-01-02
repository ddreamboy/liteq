import asyncio
import logging
from liteq import task, QueueManager, enqueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@task(queue="tasks")
async def process_task(task_id: int, priority: int):
    """Process a task"""
    logging.info(f"Processing task {task_id} (priority: {priority})")
    await asyncio.sleep(0.5)


async def main():
    manager = QueueManager(db_path="priority_example.db")
    manager.initialize()

    manager.add_worker("worker-1", queues=["tasks"])

    logging.info("Enqueueing tasks with different priorities...")

    # Enqueue tasks with different priorities
    # Higher priority runs first!
    enqueue(
        "process_task", {"task_id": 1, "priority": 1}, queue="tasks", priority=1
    )
    enqueue(
        "process_task",
        {"task_id": 2, "priority": 100},
        queue="tasks",
        priority=100,
    )  # VIP
    enqueue(
        "process_task", {"task_id": 3, "priority": 5}, queue="tasks", priority=5
    )
    enqueue(
        "process_task", {"task_id": 4, "priority": 50}, queue="tasks", priority=50
    )
    enqueue(
        "process_task", {"task_id": 5, "priority": 10}, queue="tasks", priority=10
    )

    print("Tasks enqueued in order: 1, 2, 3, 4, 5")
    print(
        "Expected execution order by priority: 2(100), 4(50), 5(10), 3(5), 1(1)\n"
    )

    # Start processing
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
