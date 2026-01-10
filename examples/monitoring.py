import asyncio
import logging
import sys
import time
from liteq import task
from liteq.db import init_db
from liteq.monitoring import (
    get_queue_stats,
    get_failed_tasks,
    get_recent_tasks,
    list_queues,
    get_active_workers,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@task(queue="jobs", max_retries=2)
async def flaky_job(job_id: int, should_fail: bool = False):
    """A job that might fail"""
    logging.info(f"Running job {job_id}")
    await asyncio.sleep(0.5)

    if should_fail:
        raise Exception(f"Job {job_id} failed intentionally!")

    logging.info(f"Job {job_id} completed")
    return {"job_id": job_id, "status": "success"}


def enqueue_jobs():
    """Enqueue test jobs"""
    init_db()
    
    logging.info("Enqueueing jobs...")

    # Enqueue successful jobs
    for i in range(1, 6):
        task_id = flaky_job.delay(job_id=i, should_fail=False)
        logging.info(f"Enqueued job {i}: task_id={task_id}")

    # Enqueue some jobs that will fail
    for i in range(6, 9):
        task_id = flaky_job.delay(job_id=i, should_fail=True)
        logging.info(f"Enqueued failing job {i}: task_id={task_id}")
    
    logging.info("\nTo process jobs, run:")
    logging.info("  liteq worker --app examples/monitoring.py --queues jobs")
    logging.info("\nTo monitor, run:")
    logging.info("  python examples/monitoring.py monitor")


def monitor_queues():
    """Monitor queues and tasks"""
    logging.info("Starting monitoring... (Ctrl+C to stop)")
    
    try:
        while True:
            print("\n" + "=" * 60)
            print("QUEUE MONITORING")
            print("=" * 60)

            # Get overall stats
            stats = get_queue_stats()
            if stats:
                for stat in stats:
                    print(f"Queue '{stat['queue']}' - {stat['status']}: {stat['count']} tasks")
            else:
                print("No tasks in database")

            # List all queues
            queues = list_queues()
            print(f"\nAll queues: {', '.join(queues) if queues else 'none'}")

            # Check for failed tasks
            failed = get_failed_tasks(limit=5)
            if failed:
                print(f"\nFailed tasks: {len(failed)}")
                for task in failed[:3]:  # Show first 3
                    print(f"   Task {task['id']}: {task['name']} - Attempts: {task['attempts']}")
                    if task.get('error'):
                        print(f"     Error: {task['error'][:100]}")
            
            # Recent tasks
            recent = get_recent_tasks(limit=5)
            if recent:
                print(f"\nRecent tasks: {len(recent)}")
                for task in recent[:3]:
                    print(f"   {task['id']}: {task['name']} ({task['status']})")
            
            # Active workers
            workers = get_active_workers()
            if workers:
                print(f"\nActive workers: {len(workers)}")
                for worker in workers:
                    print(f"   {worker['worker_id']}: {worker['queues']} (concurrency={worker['concurrency']})")
            else:
                print("\nNo active workers")

            print("=" * 60)

            time.sleep(3)  # Monitor every 3 seconds
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_queues()
    else:
        enqueue_jobs()
            
            # Active workers
            workers = get_active_workers()
            if workers:
                print(f"\nActive workers: {len(workers)}")
                for worker in workers:
                    print(f"   {worker['worker_id']}: {worker['queues']} (concurrency={worker['concurrency']})")
            else:
                print("\nNo active workers")

            print("=" * 60)

            time.sleep(3)  # Monitor every 3 seconds
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

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
