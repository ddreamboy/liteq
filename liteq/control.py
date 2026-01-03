import json
import logging
from typing import Optional, Any
from liteq.db import get_conn, get_db_transaction

logger = logging.getLogger(__name__)


def cancel_task(task_id: int) -> bool:
    """
    Request cancellation of a task (cooperative)

    The task must check ctx.cancelled periodically to honor this request

    Args:
        task_id: ID of the task to cancel

    Returns:
        True if cancellation request was set, False if task not found or already finished
    """
    with get_db_transaction() as conn:
        result = conn.execute(
            """
            UPDATE tasks
            SET cancel_requested=1,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND status IN ('pending', 'running', 'retry')
            """,
            (task_id,),
        )

        if result.rowcount > 0:
            logger.info(f"Cancellation requested for task {task_id}")
            return True
        return False


def pause_task(task_id: int) -> bool:
    """
    Request pause of a task (cooperative)

    The task must check ctx.paused periodically to honor this request

    Args:
        task_id: ID of the task to pause

    Returns:
        True if pause request was set, False if task not found or already finished
    """
    with get_db_transaction() as conn:
        result = conn.execute(
            """
            UPDATE tasks
            SET paused_requested=1,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND status IN ('pending', 'running', 'retry')
            """,
            (task_id,),
        )

        if result.rowcount > 0:
            logger.info(f"Pause requested for task {task_id}")
            return True
        return False


def resume_task(task_id: int) -> bool:
    """
    Resume a paused task

    Args:
        task_id: ID of the task to resume

    Returns:
        True if task was resumed, False otherwise
    """
    with get_db_transaction() as conn:
        result = conn.execute(
            """
            UPDATE tasks
            SET status='pending',
                paused_requested=0,
                run_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND status='paused'
            """,
            (task_id,),
        )

        if result.rowcount > 0:
            logger.info(f"Task {task_id} resumed")
            return True
        return False


def get_task_result(task_id: int) -> Optional[Any]:
    """
    Get the result of a completed task

    Args:
        task_id: ID of the task

    Returns:
        Task result (deserialized from JSON) or None if not available
    """
    conn = get_conn()
    row = conn.execute("SELECT result, status FROM tasks WHERE id=?", (task_id,)).fetchone()

    if not row:
        return None

    if row["result"]:
        return json.loads(row["result"])

    return None


def get_task_status(task_id: int) -> Optional[dict]:
    """
    Get detailed status of a task

    Args:
        task_id: ID of the task

    Returns:
        Dictionary with task details or None if not found
    """
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, name, status, queue, attempts, max_attempts,
               created_at, updated_at, finished_at, 
               error_message, progress, result,
               cancel_requested, paused_requested, worker_id
        FROM tasks WHERE id=?
        """,
        (task_id,),
    ).fetchone()

    if not row:
        return None

    task_info = dict(row)

    # Parse JSON fields
    if task_info.get("progress"):
        task_info["progress"] = json.loads(task_info["progress"])
    if task_info.get("result"):
        task_info["result"] = json.loads(task_info["result"])

    return task_info


def get_task_progress(task_id: int) -> Optional[dict]:
    """
    Get the progress of a task

    Args:
        task_id: ID of the task

    Returns:
        Progress data or None if not available
    """
    conn = get_conn()
    row = conn.execute("SELECT progress FROM tasks WHERE id=?", (task_id,)).fetchone()

    if not row or not row["progress"]:
        return None

    return json.loads(row["progress"])
