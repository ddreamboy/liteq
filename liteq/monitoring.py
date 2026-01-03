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


def get_active_workers():
    """
    Get list of active workers with their current tasks

    Returns:
        List of worker dictionaries with status information
    """
    conn = get_conn()
    workers = conn.execute("""
        SELECT 
            worker_id,
            COUNT(*) as active_tasks,
            MAX(heartbeat_at) as last_heartbeat,
            GROUP_CONCAT(DISTINCT queue) as queues
        FROM tasks
        WHERE status='running' AND worker_id IS NOT NULL
        GROUP BY worker_id
        ORDER BY worker_id
    """).fetchall()

    return [dict(row) for row in workers]


def get_recent_tasks(limit=50, queue=None, status=None):
    """
    Get recent tasks

    Args:
        limit: Maximum number of tasks to return
        queue: Specific queue name (None = all queues)
        status: Specific status (None = all statuses)

    Returns:
        List of task dictionaries
    """
    conn = get_conn()

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if queue:
        query += " AND queue=?"
        params.append(queue)

    if status:
        query += " AND status=?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    tasks = conn.execute(query, params).fetchall()
    return [dict(task) for task in tasks]


def get_task_timeline(hours=24):
    """
    Get task completion timeline for charts

    Args:
        hours: Number of hours to look back

    Returns:
        List of hourly statistics
    """
    conn = get_conn()
    timeline = conn.execute(
        """
        SELECT 
            strftime('%Y-%m-%d %H:00', created_at) as hour,
            status,
            COUNT(*) as count
        FROM tasks
        WHERE created_at >= datetime('now', '-' || ? || ' hours')
        GROUP BY hour, status
        ORDER BY hour DESC
    """,
        (hours,),
    ).fetchall()

    return [dict(row) for row in timeline]


def get_worker_performance():
    """
    Get performance statistics per worker

    Returns:
        List of worker performance dictionaries
    """
    conn = get_conn()
    stats = conn.execute("""
        SELECT 
            worker_id,
            status,
            COUNT(*) as task_count,
            AVG(CAST((julianday(finished_at) - julianday(updated_at)) * 86400 AS REAL)) as avg_duration_seconds,
            MAX(finished_at) as last_task_finished
        FROM tasks
        WHERE worker_id IS NOT NULL
        GROUP BY worker_id, status
        ORDER BY worker_id, status
    """).fetchall()

    return [dict(row) for row in stats]
