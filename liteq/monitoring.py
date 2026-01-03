from liteq.db import get_conn, get_db_transaction


def get_queue_stats(queue=None):
    """
    Get current queue statistics

    Args:
        queue: Specific queue name (None = all queues)

    Returns:
        Dictionary with statistics by status and queue
    """
    conn = get_conn()

    if queue:
        stats = conn.execute(
            """
            SELECT 
                status,
                COUNT(*) as count,
                AVG(attempts) as avg_attempts,
                MIN(priority) as min_priority,
                MAX(priority) as max_priority
            FROM tasks
            WHERE queue=?
            GROUP BY status
        """,
            (queue,),
        ).fetchall()
    else:
        stats = conn.execute("""
            SELECT 
                queue,
                status,
                COUNT(*) as count,
                AVG(attempts) as avg_attempts,
                MIN(priority) as min_priority,
                MAX(priority) as max_priority
            FROM tasks
            GROUP BY queue, status
        """).fetchall()

    return [dict(row) for row in stats]


def get_task_by_id(task_id):
    """
    Get task details by ID

    Args:
        task_id: Task ID

    Returns:
        Task dictionary or None
    """
    conn = get_conn()
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(task) if task else None


def get_failed_tasks(limit=100, queue=None):
    """
    Get recent failed tasks

    Args:
        limit: Maximum number of tasks to return
        queue: Specific queue name (None = all queues)

    Returns:
        List of failed task dictionaries
    """
    conn = get_conn()

    if queue:
        tasks = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status='failed' AND queue=?
            ORDER BY updated_at DESC
            LIMIT ?
        """,
            (queue, limit),
        ).fetchall()
    else:
        tasks = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status='failed'
            ORDER BY updated_at DESC
            LIMIT ?
        """,
            (limit,),
        ).fetchall()

    return [dict(task) for task in tasks]


def retry_task(task_id):
    """
    Retry a failed task

    Args:
        task_id: Task ID to retry
    """
    with get_db_transaction() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status='pending',
                attempts=0,
                run_at=CURRENT_TIMESTAMP,
                last_error=NULL
            WHERE id=? AND status='failed'
        """,
            (task_id,),
        )


def get_pending_count(queue=None):
    """
    Get count of pending tasks

    Args:
        queue: Specific queue name (None = all queues)

    Returns:
        Number of pending tasks
    """
    conn = get_conn()

    if queue:
        result = conn.execute(
            """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status='pending' AND queue=?
        """,
            (queue,),
        ).fetchone()
    else:
        result = conn.execute("""
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status='pending'
        """).fetchone()

    return result["count"] if result else 0


def list_queues():
    """
    Get list of all queue names

    Returns:
        List of queue names
    """
    conn = get_conn()
    queues = conn.execute("""
        SELECT DISTINCT queue
        FROM tasks
        ORDER BY queue
    """).fetchall()

    return [row["queue"] for row in queues]
