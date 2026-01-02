import asyncio
import json
import traceback
from db import get_conn
from registry import get_task

POLL_INTERVAL = 1

async def worker(worker_id: str):
    conn = get_conn()

    while True:
        task = conn.execute("""
            SELECT * FROM tasks
            WHERE status='pending'
              AND run_at <= CURRENT_TIMESTAMP
            ORDER BY id
            LIMIT 1
        """).fetchone()

        if not task:
            await asyncio.sleep(POLL_INTERVAL)
            continue

        updated = conn.execute("""
            UPDATE tasks
            SET status='running',
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND status='pending'
        """, (task["id"],)).rowcount
        conn.commit()

        if updated == 0:
            continue

        try:
            func = get_task(task["name"])
            payload = json.loads(task["payload"])

            await func(**payload)

            conn.execute("""
                UPDATE tasks
                SET status='done',
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (task["id"],))

        except Exception as e:
            attempts = task["attempts"] + 1
            tb = traceback.format_exc()

            if attempts >= task["max_retries"]:
                conn.execute("""
                    UPDATE tasks
                    SET status='failed',
                        attempts=?,
                        last_error=?
                    WHERE id=?
                """, (attempts, tb, task["id"]))
            else:
                conn.execute("""
                    UPDATE tasks
                    SET status='pending',
                        attempts=?,
                        run_at=datetime('now', '+5 seconds'),
                        last_error=?
                    WHERE id=?
                """, (attempts, tb, task["id"]))

        conn.commit()
