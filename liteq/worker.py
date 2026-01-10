import asyncio
import inspect
import json
import os
import socket
import time
from concurrent.futures import ProcessPoolExecutor

from .core import TASK_REGISTRY
from .db import get_conn


def _run_in_subprocess(t_id, t_name, t_payload):
    fn = TASK_REGISTRY.get(t_name)
    if not fn:
        return

    args = json.loads(t_payload)
    worker_id = f"process-{os.getpid()}"

    try:
        if inspect.iscoroutinefunction(fn):
            res = asyncio.run(fn(*args["args"], **args["kwargs"]))
        else:
            res = fn(*args["args"], **args["kwargs"])

        with get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='done', result=?, finished_at=CURRENT_TIMESTAMP, worker_id=? WHERE id=?",
                (json.dumps(res), worker_id, t_id),
            )
    except Exception as e:
        with get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='failed', error=?, worker_id=? WHERE id=?",
                (str(e), worker_id, t_id),
            )


class Worker:
    def __init__(self, queues, concurrency):
        self.queues = [q.strip() for q in queues]
        self.concurrency = concurrency
        self.pool = ProcessPoolExecutor(max_workers=concurrency)
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}"

    def _heartbeat(self):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO workers (worker_id, hostname, queues, concurrency, last_heartbeat)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(worker_id) DO UPDATE SET last_heartbeat=CURRENT_TIMESTAMP
            """,
                (
                    self.worker_id,
                    socket.gethostname(),
                    ",".join(self.queues),
                    self.concurrency,
                ),
            )

    def run(self):
        print(f"[*] LiteQ Worker {self.worker_id} started.")
        try:
            while True:
                self._heartbeat()
                self._fetch_and_run()
                time.sleep(0.5)
        finally:
            with get_conn() as conn:
                conn.execute("DELETE FROM workers WHERE worker_id=?", (self.worker_id,))
            print("\n[*] Worker stopped.")

    def _fetch_and_run(self):
        with get_conn() as conn:
            q_marks = ",".join(["?"] * len(self.queues))
            row = conn.execute(
                f"""
                UPDATE tasks SET status='running' 
                WHERE id = (
                    SELECT id FROM tasks 
                    WHERE status='pending' AND queue IN ({q_marks})
                    AND run_at <= CURRENT_TIMESTAMP
                    ORDER BY priority DESC, id ASC LIMIT 1
                ) RETURNING id, name, payload
            """,
                self.queues,
            ).fetchone()

            if row:
                self.pool.submit(_run_in_subprocess, row["id"], row["name"], row["payload"])
