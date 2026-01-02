import json
import datetime
from db import get_conn

def enqueue(task_name, payload=None, delay=0, max_retries=3):
    payload = payload or {}
    run_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay)

    conn = get_conn()
    conn.execute("""
        INSERT INTO tasks (name, payload, run_at, max_retries)
        VALUES (?, ?, ?, ?)
    """, (
        task_name,
        json.dumps(payload),
        run_at,
        max_retries
    ))
    conn.commit()
