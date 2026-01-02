import asyncio
import logging
from liteq import (
    task,
    QueueManager,
    enqueue,
    get_queue_stats,
    get_failed_tasks,
    retry_task,
    get_pending_count,
    recover_stuck_tasks,
    cleanup_old_tasks,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@task(queue="jobs", max_retries=2)
async def flaky_job(job_id: int, should_fail: bool = False):
    """A job that might fail"""
    logging.info(f"Running job {job_id}")
    await asyncio.sleep(0.5)

    if should_fail:
        raise Exception(f"Job {job_id} failed intentionally!")

    logging.info(f"Job {job_id} completed")


async def monitor_queues(manager):
    """Background monitoring task"""
    await asyncio.sleep(2)  # Wait for some tasks to process

    while True:
        logging.info("=" * 60)
        logging.info("QUEUE MONITORING")
        logging.info("=" * 60)

        # Get overall stats
        stats = get_queue_stats()
        for stat in stats:
            logging.info(f"Queue '{stat['queue']}' - {stat['status']}: {stat['count']} tasks")

        # Get pending count
        pending = get_pending_count(queue="jobs")
        logging.info(f"Pending tasks in 'jobs' queue: {pending}")

        # Check for failed tasks
        failed = get_failed_tasks(limit=5, queue="jobs")
        if failed:
            logging.info(f"Failed tasks: {len(failed)}")
            for task in failed[:3]:  # Show first 3
                logging.info(f"   Task {task['id']}: {task['name']} - Attempts: {task['attempts']}")

        # Recover stuck tasks (if any)
        recovered = recover_stuck_tasks(timeout_minutes=1)
        if recovered > 0:
            logging.info(f"Recovered {recovered} stuck tasks")

        logging.info("=" * 60)

        await asyncio.sleep(5)  # Monitor every 5 seconds


async def main():
    manager = QueueManager(db_path="monitoring_example.db")
    manager.initialize()

    manager.add_worker("worker-1", queues=["jobs"])

    logging.info("Enqueueing jobs...")

    # Enqueue successful jobs
    for i in range(1, 6):
        enqueue("flaky_job", {"job_id": i, "should_fail": False}, queue="jobs")

    # Enqueue some jobs that will fail
    for i in range(6, 9):
        enqueue("flaky_job", {"job_id": i, "should_fail": True}, queue="jobs")

    # Start monitoring in background
    monitor_task = asyncio.create_task(monitor_queues(manager))

    # Start processing
    try:
        await manager.start()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        monitor_task.cancel()
        await manager.stop()

        # Show final stats
        logging.info("FINAL STATISTICS:")
        stats = get_queue_stats()
        for stat in stats:
            logging.info(f"   {stat['queue']}/{stat['status']}: {stat['count']}")

        # Show failed tasks
        failed = get_failed_tasks(queue="jobs")
        if failed:
            logging.info(f"Total failed tasks: {len(failed)}")
            logging.info("You can retry failed tasks using retry_task(task_id)")


if __name__ == "__main__":
    asyncio.run(main())
