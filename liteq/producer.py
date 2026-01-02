import json
import datetime
import logging
from liteq.db import get_conn, get_db_transaction

logger = logging.getLogger(__name__)


def enqueue(task_name, payload=None, delay=0, max_retries=3, priority=0, queue="default"):
    """
    Enqueue a task for processing

    Args:
        task_name: Name of the registered task
        payload: Dictionary with task arguments
        delay: Delay in seconds before task execution
        max_retries: Maximum number of retry attempts
        priority: Task priority (higher = more important)
        queue: Queue name (default: 'default')

    Returns:
        Task ID
    """
    payload = payload or {}
    run_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay)

    with get_db_transaction() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (name, payload, run_at, max_retries, priority, queue)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (task_name, json.dumps(payload), run_at, max_retries, priority, queue),
        )
        task_id = cursor.lastrowid

    logger.info(
        f"Enqueued task {task_id} ({task_name}) to queue '{queue}' with priority {priority}"
    )
    return task_id


def enqueue_many(tasks):
    """
    Enqueue multiple tasks in a single transaction

    Args:
        tasks: List of dicts with keys: task_name, payload, delay, max_retries, priority, queue

    Returns:
        List of task IDs
    """
    task_ids = []
    with get_db_transaction() as conn:
        for task in tasks:
            task_name = task["task_name"]
            payload = task.get("payload", {})
            delay = task.get("delay", 0)
            max_retries = task.get("max_retries", 3)
            priority = task.get("priority", 0)
            queue = task.get("queue", "default")

            run_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=delay
            )

            cursor = conn.execute(
                """
                INSERT INTO tasks (name, payload, run_at, max_retries, priority, queue)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    task_name,
                    json.dumps(payload),
                    run_at,
                    max_retries,
                    priority,
                    queue,
                ),
            )

            task_ids.append(cursor.lastrowid)

    logger.info(f"Enqueued {len(task_ids)} tasks")
    return task_ids
