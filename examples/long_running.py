import asyncio
import logging
from liteq import (
    task,
    QueueManager,
    enqueue,
    cancel_task,
    get_task_status,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@task
async def process_large_dataset(ctx, dataset_size: int = 1000):
    """
    Long-running task that processes a large dataset

    Features:
    - Periodic progress checkpoints
    - Heartbeat handled automatically by worker
    - Cooperative cancellation
    - Result storage
    """
    logging.info(
        f"[Task {ctx.task_id}] Starting processing of {dataset_size} items"
    )

    # Check for previous progress
    progress = ctx.load_progress()
    if progress:
        start_from = progress.get("payload", {}).get("processed", 0)
        logging.info(f"[Task {ctx.task_id}] Resuming from item {start_from}")
    else:
        start_from = 0

    results = []

    for i in range(start_from, dataset_size):
        # Check for cancellation
        if ctx.cancelled:
            logging.info(
                f"[Task {ctx.task_id}] Cancellation requested, stopping at {i}"
            )
            ctx.save_progress(
                f"cancelled_at_{i}", {"processed": i, "results": results}
            )
            return {"status": "cancelled", "processed": i}

        # Check for pause
        if ctx.paused:
            logging.info(f"[Task {ctx.task_id}] Pause requested, stopping at {i}")
            ctx.save_progress(
                f"paused_at_{i}", {"processed": i, "results": results}
            )
            return {"status": "paused", "processed": i}

        # Simulate processing
        await asyncio.sleep(0.1)
        results.append(f"result_{i}")

        # Save checkpoint every 100 items
        if (i + 1) % 100 == 0:
            ctx.save_progress(
                f"step_{i + 1}", {"processed": i + 1, "total": dataset_size}
            )
            logging.info(
                f"[Task {ctx.task_id}] Checkpoint: {i + 1}/{dataset_size} items processed"
            )

        # Heartbeat is updated automatically by worker in background

    # Save final result
    final_result = {
        "status": "completed",
        "total_processed": dataset_size,
        "results_count": len(results),
    }

    ctx.save_result(final_result)
    logging.info(f"[Task {ctx.task_id}] Processing completed!")

    return final_result


@task
async def compute_pi(ctx, iterations: int = 10000000):
    """
    CPU-intensive long-running task with checkpoints
    """
    logging.info(f"[Task {ctx.task_id}] Computing Pi with {iterations} iterations")

    # Check for previous progress
    progress = ctx.load_progress()
    if progress:
        start = progress.get("payload", {}).get("current_iteration", 0)
        inside = progress.get("payload", {}).get("inside_circle", 0)
        logging.info(f"[Task {ctx.task_id}] Resuming from iteration {start}")
    else:
        start = 0
        inside = 0

    import random

    for i in range(start, iterations):
        if ctx.cancelled:
            logging.info(f"[Task {ctx.task_id}] Cancelled at iteration {i}")
            return {"status": "cancelled", "iterations": i}

        x = random.random()
        y = random.random()

        if x * x + y * y <= 1:
            inside += 1

        # Checkpoint every 1M iterations
        if (i + 1) % 1000000 == 0:
            pi_estimate = (inside / (i + 1)) * 4
            ctx.save_progress(
                f"iteration_{i + 1}",
                {
                    "current_iteration": i + 1,
                    "inside_circle": inside,
                    "pi_estimate": pi_estimate,
                },
            )
            logging.info(
                f"[Task {ctx.task_id}] Checkpoint: {i + 1}/{iterations}, Pi ≈ {pi_estimate:.6f}"
            )

    pi_value = (inside / iterations) * 4
    result = {
        "status": "completed",
        "pi_estimate": pi_value,
        "iterations": iterations,
    }

    ctx.save_result(result)
    logging.info(f"[Task {ctx.task_id}] Pi ≈ {pi_value:.6f}")

    return result


async def demo_long_running_tasks():
    """Demonstrate long-running task features"""

    # Create manager with watchdog enabled
    manager = QueueManager(
        db_path="long_running_demo.db",
        enable_watchdog=True,
        watchdog_lease_timeout=30,  # 30 seconds before task considered stuck
        watchdog_check_interval=10,  # Check every 10 seconds
    )

    manager.initialize()

    # Add worker
    manager.add_worker("worker-1", queues=["default"])

    # Enqueue long-running tasks
    task1_id = enqueue(
        "process_large_dataset", {"dataset_size": 500}, max_attempts=5
    )
    task2_id = enqueue("compute_pi", {"iterations": 5000000}, max_attempts=3)

    logging.info(f"\nEnqueued tasks: {task1_id}, {task2_id}")
    logging.info("You can monitor task progress in another terminal with:")
    logging.info(
        f"\tpython -c 'from liteq import get_task_progress; logging.info(get_task_progress({task1_id}))'"
    )
    logging.info("\nTo cancel a task, run:")
    logging.info(
        f"\tpython -c 'from liteq import cancel_task; cancel_task({task1_id})'"
    )

    try:
        await asyncio.wait_for(manager.start(), timeout=60)
    except asyncio.TimeoutError:
        logging.info("\nDemo timeout reached")
    except KeyboardInterrupt:
        logging.info("\nInterrupted by user")
    finally:
        await manager.stop()

        logging.info("Final Task Status:")

        for task_id in [task1_id, task2_id]:
            status = get_task_status(task_id)
            if status:
                logging.info(f"\nTask {task_id}:")
                logging.info(f"  Status: {status['status']}")
                logging.info(
                    f"  Attempts: {status['attempts']}/{status['max_attempts']}"
                )
                if status.get("progress"):
                    logging.info(f"  Progress: {status['progress']}")
                if status.get("result"):
                    logging.info(f"  Result: {status['result']}")


async def demo_cancellation():
    """Demonstrate task cancellation"""

    manager = QueueManager(db_path="cancellation_demo.db")
    manager.initialize()
    manager.add_worker("worker-cancel", queues=["default"])

    # Enqueue a long task
    task_id = enqueue("process_large_dataset", {"dataset_size": 10000})
    logging.info(f"Enqueued task {task_id}")

    # Start worker in background
    worker_task = asyncio.create_task(manager.start())

    # Wait a bit, then cancel
    await asyncio.sleep(5)
    logging.info(f"\n🛑 Requesting cancellation for task {task_id}")
    cancel_task(task_id)

    # Wait for task to handle cancellation
    await asyncio.sleep(3)

    # Stop manager
    await manager.stop()
    await worker_task

    # Check final status
    status = get_task_status(task_id)
    logging.info(f"\nFinal status: {status}")


if __name__ == "__main__":
    logging.info("""
╔══════════════════════════════════════════════════════════════╗
║         Liteq Long-Running Tasks Demo                        ║
║                                                              ║
║  Features demonstrated:                                      ║
║  ✓ Heartbeat mechanism                                      ║
║  ✓ Progress checkpoints                                     ║
║  ✓ Cooperative cancellation                                 ║
║  ✓ Result storage                                           ║
║  ✓ Watchdog for stuck task recovery                         ║
╚══════════════════════════════════════════════════════════════╝
    """)

    choice = (
        input(
            "\nChoose demo:\n1. Long-running tasks\n2. Cancellation demo\n\nChoice [1]: "
        ).strip()
        or "1"
    )

    if choice == "2":
        asyncio.run(demo_cancellation())
    else:
        asyncio.run(demo_long_running_tasks())
