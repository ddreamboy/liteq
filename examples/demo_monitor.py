import asyncio
import time
import random
from liteq import task, QueueManager, enqueue
from liteq.web import run_monitor
import threading


@task(queue="emails", max_retries=3)
def send_email(email: str, subject: str):
    print(f"Sending email to {email}: {subject}")
    time.sleep(random.uniform(1, 3))
    if random.random() < 0.1:
        raise ValueError(f"Failed to send email to {email}")
    return f"Email sent to {email}"


@task(queue="processing", max_retries=1)
async def process_data(data_id: int):
    print(f"Processing data {data_id}")
    await asyncio.sleep(random.uniform(30, 120))
    if random.random() < 0.15:
        raise RuntimeError(f"Failed to process data {data_id}")
    return f"Data {data_id} processed successfully"


@task(queue="notifications", max_retries=2)
def send_notification(user_id: int, message: str):
    print(f"Notification to user {user_id}: {message}")
    time.sleep(random.uniform(0.5, 1.5))
    return f"Notification sent to user {user_id}"


async def generate_continuous_tasks():
    task_counter = 0

    while True:
        num_tasks = random.randint(3, 5)

        for _ in range(num_tasks):
            task_type = random.choice(["email", "data", "notification"])

            if task_type == "email":
                enqueue(
                    "send_email",
                    {
                        "email": f"user{task_counter}@example.com",
                        "subject": f"Test Email {task_counter}",
                    },
                    queue="emails",
                    priority=random.randint(1, 10),
                )
            elif task_type == "data":
                enqueue(
                    "process_data",
                    {"data_id": task_counter},
                    queue="processing",
                    priority=random.randint(1, 20),
                )
            else:
                enqueue(
                    "send_notification",
                    {
                        "user_id": task_counter,
                        "message": f"Hello from task {task_counter}",
                    },
                    queue="notifications",
                )

            task_counter += 1

        print(f"Generated {num_tasks} tasks (total: {task_counter})")

        await asyncio.sleep(random.uniform(5, 10))


async def run_workers():
    manager = QueueManager(db_path="demo_tasks.db")
    manager.initialize()

    manager.add_worker("worker-emails", queues=["emails"])
    manager.add_worker("worker-processing", queues=["processing"])
    manager.add_worker("worker-notifications", queues=["notifications"])
    manager.add_worker("worker-all", queues=["emails", "processing", "notifications"])

    print("Starting workers...")
    await manager.start()


def start_monitor_thread():
    print("\nOpen your browser to: http://127.0.0.1:5151")

    thread = threading.Thread(
        target=run_monitor,
        kwargs={"db_path": "demo_tasks.db", "host": "127.0.0.1", "port": 5151},
        daemon=True,
    )
    thread.start()
    return thread


async def main():
    start_monitor_thread()

    await asyncio.sleep(2)

    generator_task = asyncio.create_task(generate_continuous_tasks())

    try:
        await run_workers()
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        generator_task.cancel()
        await asyncio.sleep(1)
        print("Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
