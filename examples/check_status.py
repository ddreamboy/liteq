"""Example: How to check task status by ID"""

import time

from liteq import get_task_status, task
from liteq.db import init_db


@task(max_retries=3)
def process_data(data_id: int):
    """Simulate data processing"""
    print(f"Processing data {data_id}...")
    time.sleep(2)
    return {"data_id": data_id, "status": "processed", "rows": 1000}


if __name__ == "__main__":
    # Initialize database
    init_db()

    # Enqueue task
    task_id = process_data.delay(data_id=42)
    print(f"Task enqueued with ID: {task_id}\n")

    # Poll task status
    print("Checking task status...\n")
    while True:
        status = get_task_status(task_id)

        if status:
            print(f"Task ID: {status['id']}")
            print(f"Status: {status['status']}")
            print(f"Queue: {status['queue']}")
            print(f"Attempts: {status['attempts']}/{status['max_retries']}")

            if status["status"] == "done":
                print("\n✅ Task completed!")
                print(f"Result: {status['result']}")
                break
            elif status["status"] == "failed":
                print("\n❌ Task failed!")
                print(f"Error: {status['error']}")
                break
            elif status["status"] == "running":
                print(f"Worker: {status['worker_id']}")
                print(f"Started at: {status['started_at']}")

            print("-" * 50)
            time.sleep(1)
        else:
            print(f"Task {task_id} not found")
            break

    print("\nTo process this task, run:")
    print("  liteq worker --app examples/check_status.py")
