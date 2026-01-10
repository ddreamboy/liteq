from .db import get_conn


def get_queue_stats():
    conn = get_conn()
    stats = conn.execute("""
        SELECT queue, status, COUNT(*) as count 
        FROM tasks GROUP BY queue, status
    """).fetchall()
    return [dict(row) for row in stats]


def get_recent_tasks(limit=50):
    conn = get_conn()
    tasks = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(row) for row in tasks]


def list_queues():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT queue FROM tasks").fetchall()
    return [row["queue"] for row in rows]


def get_failed_tasks(limit=50):
    conn = get_conn()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE status='failed' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in tasks]


def get_active_workers():
    conn = get_conn()
    workers = conn.execute("""
        SELECT * FROM workers 
        WHERE last_heartbeat > datetime('now', '-15 seconds')
    """).fetchall()

    result = []
    for w in workers:
        d = dict(w)
        d["queues"] = d["queues"].split(",") if d["queues"] else []

        active_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='running' AND worker_id LIKE ?",
            (f"%{d['worker_id']}%",),
        ).fetchone()[0]

        d["active_tasks"] = active_tasks
        result.append(d)

    return result
