"""
Task timeout example for LiteQ

This example demonstrates task timeouts and stuck task handling.

Run this example:
1. python examples/timeout_example.py  # Enqueue tasks
2. liteq worker --app examples/timeout_example.py --timeout 5  # Worker with 5s timeout
3. liteq monitor  # View dashboard
"""

import asyncio
import time
from datetime import datetime

from liteq import task
from liteq.db import init_db


@task(queue="default", timeout=5)
def quick_task(name: str):
    """Task that completes quickly"""
    print(f"[{datetime.now()}] Starting quick task: {name}")
    time.sleep(1)
    print(f"[{datetime.now()}] Quick task done: {name}")
    return {"status": "success", "name": name}


@task(queue="default", timeout=10)
async def slow_async_task(name: str):
    """Async task that takes some time"""
    print(f"[{datetime.now()}] Starting slow async task: {name}")
    await asyncio.sleep(3)
    print(f"[{datetime.now()}] Slow async task done: {name}")
    return {"status": "success", "name": name}


@task(queue="default")
def stuck_task(name: str):
    """Task that will get stuck (simulates hung process)"""
    print(f"[{datetime.now()}] Starting stuck task: {name}")
    print("This task will hang forever...")
    time.sleep(999999)  # Simulates a stuck task
    return {"status": "never_reached"}


@task(queue="default", timeout=30)
def long_running_task(duration: int):
    """Task with configurable duration"""
    print(f"[{datetime.now()}] Starting long task (duration: {duration}s)")
    time.sleep(duration)
    print(f"[{datetime.now()}] Long task completed")
    return {"status": "success", "duration": duration}


if __name__ == "__main__":
    # Initialize database
    init_db()

    print("Enqueueing test tasks...")
    print("=" * 60)

    # Enqueue quick tasks (should complete)
    task_id_1 = quick_task.delay("Task 1")
    print(f"✓ Enqueued quick_task (ID: {task_id_1})")

    task_id_2 = quick_task.delay("Task 2")
    print(f"✓ Enqueued quick_task (ID: {task_id_2})")

    # Enqueue slow async task (should complete)
    task_id_3 = slow_async_task.delay("Async Task")
    print(f"✓ Enqueued slow_async_task (ID: {task_id_3})")

    # Enqueue stuck task (will be killed by worker timeout)
    task_id_4 = stuck_task.delay("Stuck Task")
    print(f"✓ Enqueued stuck_task (ID: {task_id_4}) - will timeout!")

    # Enqueue long running tasks
    task_id_5 = long_running_task.delay(duration=3)
    print(f"✓ Enqueued long_running_task 3s (ID: {task_id_5})")

    task_id_6 = long_running_task.delay(duration=20)
    print(f"✓ Enqueued long_running_task 20s (ID: {task_id_6}) - may timeout!")

    print("\n" + "=" * 60)
    print("Tasks enqueued!")
    print("=" * 60)
    print("\nStart worker with timeout:")
    print("  liteq worker --app examples/timeout_example.py --timeout 5")
    print("\nThis will:")
    print("  - Complete quick tasks (1s)")
    print("  - Complete slow async task (3s)")
    print("  - KILL stuck task after 5s timeout")
    print("  - KILL long running 20s task after 5s timeout")
    print("\nView results in dashboard:")
    print("  liteq monitor")
    print("  http://localhost:5151")
    print("\nWithout timeout (tasks may hang):")
    print("  liteq worker --app examples/timeout_example.py")
