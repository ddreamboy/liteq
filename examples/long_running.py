import asyncio
import logging
from liteq import task
from liteq.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@task(max_retries=3)
async def process_large_dataset(dataset_size: int = 1000):
    """
    Long-running task that processes a large dataset
    """
    logging.info(f"Starting processing of {dataset_size} items")

    results = []
    for i in range(dataset_size):
        # Simulate processing
        await asyncio.sleep(0.01)
        results.append(f"result_{i}")

        # Log progress every 100 items
        if (i + 1) % 100 == 0:
            logging.info(f"Progress: {i + 1}/{dataset_size} items processed")

    logging.info(f"Processing completed! Processed {len(results)} items")
    
    return {
        "status": "completed",
        "total_processed": dataset_size,
        "results_count": len(results),
    }


@task(max_retries=3)
async def compute_heavy_calculation(iterations: int = 1000000):
    """
    CPU-intensive long-running task
    """
    logging.info(f"Computing with {iterations} iterations")

    result = 0
    for i in range(iterations):
        result += i ** 2
        
        # Log progress every 100k iterations
        if (i + 1) % 100000 == 0:
            logging.info(f"Progress: {i + 1}/{iterations} iterations")
    
    logging.info(f"Computation completed! Result: {result}")
    
    return {
        "status": "completed",
        "iterations": iterations,
        "result": result,
    }


@task(max_retries=2)
async def download_and_process(url: str, chunk_count: int = 50):
    """
    Simulate downloading and processing data
    """
    logging.info(f"Downloading from {url}")
    
    for i in range(chunk_count):
        await asyncio.sleep(0.1)  # Simulate download
        
        if (i + 1) % 10 == 0:
            logging.info(f"Downloaded {i + 1}/{chunk_count} chunks")
    
    logging.info(f"Download and processing complete for {url}")
    
    return {
        "url": url,
        "chunks": chunk_count,
        "status": "completed",
    }


if __name__ == "__main__":
    # Initialize database
    init_db()

    logging.info("Enqueueing long-running tasks...")

    # Enqueue long-running tasks
    task1 = process_large_dataset.delay(dataset_size=500)
    logging.info(f"Enqueued dataset processing: {task1}")

    task2 = compute_heavy_calculation.delay(iterations=1000000)
    logging.info(f"Enqueued heavy calculation: {task2}")

    task3 = download_and_process.delay(url="https://example.com/data", chunk_count=50)
    logging.info(f"Enqueued download task: {task3}")

    logging.info("\nTo process these tasks, run:")
    logging.info("  liteq worker --app examples/long_running.py --concurrency 2")
    logging.info("\nTasks will show progress in the worker logs")

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
    task1_id = enqueue("process_large_dataset", {"dataset_size": 500}, max_attempts=5)
    task2_id = enqueue("compute_pi", {"iterations": 5000000}, max_attempts=3)

    logging.info(f"\nEnqueued tasks: {task1_id}, {task2_id}")
    logging.info("You can monitor task progress in another terminal with:")
    logging.info(
        f"\tpython -c 'from liteq import get_task_progress; logging.info(get_task_progress({task1_id}))'"
    )
    logging.info("\nTo cancel a task, run:")
    logging.info(f"\tpython -c 'from liteq import cancel_task; cancel_task({task1_id})'")

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
                logging.info(f"  Attempts: {status['attempts']}/{status['max_attempts']}")
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
        input("\nChoose demo:\n1. Long-running tasks\n2. Cancellation demo\n\nChoice [1]: ").strip()
        or "1"
    )

    if choice == "2":
        asyncio.run(demo_cancellation())
    else:
        asyncio.run(demo_long_running_tasks())
