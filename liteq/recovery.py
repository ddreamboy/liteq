import logging
from liteq.db import get_db_transaction

logger = logging.getLogger(__name__)


def recover_paused(queue=None):
    """
    Recover paused tasks back to pending state

    Args:
        queue: Specific queue to recover (None = all queues)
    """
    with get_db_transaction() as conn:
        if queue:
            result = conn.execute(
                """
                UPDATE tasks
                SET status='pending',
                    worker_id=NULL,
                    paused_requested=0
                WHERE status='paused' AND queue=?
            """,
                (queue,),
            )
        else:
            result = conn.execute("""
                UPDATE tasks
                SET status='pending',
                    worker_id=NULL,
                    paused_requested=0
                WHERE status='paused'
            """)
        count = result.rowcount

    if count > 0:
        queue_info = f" in queue '{queue}'" if queue else ""
        logger.info(f"Recovered {count} paused tasks{queue_info}")


def pause_running(queue=None):
    """
    Pause all running tasks

    Args:
        queue: Specific queue to pause (None = all queues)
    """
    with get_db_transaction() as conn:
        if queue:
            result = conn.execute(
                """
                UPDATE tasks
                SET status='paused'
                WHERE status='running' AND queue=?
            """,
                (queue,),
            )
        else:
            result = conn.execute("""
                UPDATE tasks
                SET status='paused'
                WHERE status='running'
            """)
        count = result.rowcount

    if count > 0:
        queue_info = f" in queue '{queue}'" if queue else ""
        logger.info(f"Paused {count} running tasks{queue_info}")


def recover_stuck_tasks(timeout_minutes=30, queue=None):
    """
    Recover tasks that have been running for too long
    (likely from crashed workers)

    DEPRECATED: Use watchdog instead for heartbeat-based recovery

    Args:
        timeout_minutes: Minutes before a task is considered stuck
        queue: Specific queue to recover (None = all queues)
    """
    with get_db_transaction() as conn:
        if queue:
            result = conn.execute(
                """
                UPDATE tasks
                SET status='retry',
                    worker_id=NULL,
                    retry_at=datetime('now', '+5 seconds')
                WHERE status='running'
                  AND queue=?
                  AND (
                    heartbeat_at IS NULL
                    OR heartbeat_at < datetime('now', '-{} minutes')
                  )
            """.format(timeout_minutes),
                (queue,),
            )
        else:
            result = conn.execute(
                """
                UPDATE tasks
                SET status='retry',
                    worker_id=NULL,
                    retry_at=datetime('now', '+5 seconds')
                WHERE status='running'
                  AND (
                    heartbeat_at IS NULL
                    OR heartbeat_at < datetime('now', '-{} minutes')
                  )
            """.format(timeout_minutes)
            )
        count = result.rowcount

    if count > 0:
        queue_info = f" in queue '{queue}'" if queue else ""
        logger.warning(f"Recovered {count} stuck tasks{queue_info}")

    return count


def recover_retry_tasks(queue=None):
    """
    Move retry tasks that are ready back to pending

    Args:
        queue: Specific queue to recover (None = all queues)
    """
    with get_db_transaction() as conn:
        if queue:
            result = conn.execute(
                """
                UPDATE tasks
                SET status='pending',
                    run_at=CURRENT_TIMESTAMP
                WHERE status='retry'
                  AND queue=?
                  AND (retry_at IS NULL OR retry_at <= CURRENT_TIMESTAMP)
                """,
                (queue,),
            )
        else:
            result = conn.execute("""
                UPDATE tasks
                SET status='pending',
                    run_at=CURRENT_TIMESTAMP
                WHERE status='retry'
                  AND (retry_at IS NULL OR retry_at <= CURRENT_TIMESTAMP)
            """)
        count = result.rowcount

    if count > 0:
        queue_info = f" in queue '{queue}'" if queue else ""
        logger.info(f"Moved {count} retry tasks to pending{queue_info}")

    return count


def cleanup_old_tasks(days=30, queue=None):
    """
    Delete completed/failed tasks older than specified days

    Args:
        days: Age threshold in days
        queue: Specific queue to clean (None = all queues)
    """
    with get_db_transaction() as conn:
        if queue:
            result = conn.execute(
                """
                DELETE FROM tasks
                WHERE status IN ('done', 'failed')
                  AND queue=?
                  AND completed_at < datetime('now', '-{} days')
            """.format(days),
                (queue,),
            )
        else:
            result = conn.execute(
                """
                DELETE FROM tasks
                WHERE status IN ('done', 'failed')
                  AND completed_at < datetime('now', '-{} days')
            """.format(days)
            )
        count = result.rowcount

    if count > 0:
        queue_info = f" from queue '{queue}'" if queue else ""
        logger.info(f"Cleaned up {count} old tasks{queue_info}")

    return count
