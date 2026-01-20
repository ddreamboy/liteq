import asyncio
import inspect
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor

from .core import TASK_REGISTRY
from .db import get_conn


def _run_task_in_thread(t_id, t_name, t_payload, worker_id, timeout=None):
    """Execute task in thread with optional timeout"""

    fn = TASK_REGISTRY.get(t_name)
    if not fn:
        with get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='failed', error=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
                (f"Task function '{t_name}' not found in registry", t_id),
            )
        return

    args = json.loads(t_payload)

    # Update started_at timestamp
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET started_at=CURRENT_TIMESTAMP WHERE id=?",
            (t_id,),
        )

    try:
        if inspect.iscoroutinefunction(fn):
            res = asyncio.run(fn(*args["args"], **args["kwargs"]))
        else:
            res = fn(*args["args"], **args["kwargs"])

        with get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='done', result=?, finished_at=CURRENT_TIMESTAMP, worker_id=? WHERE id=?",
                (json.dumps(res) if res is not None else None, worker_id, t_id),
            )
    except Exception as e:
        import traceback

        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        with get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='failed', error=?, finished_at=CURRENT_TIMESTAMP, worker_id=? WHERE id=?",
                (error_msg, worker_id, t_id),
            )


class Worker:
    def __init__(self, queues, concurrency, task_timeout=None):
        self.queues = [q.strip() for q in queues]
        self.concurrency = concurrency
        self.task_timeout = task_timeout  # Timeout in seconds for stuck tasks
        self.pool = ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="liteq-worker")
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}"
        self.running_tasks = {}  # task_id -> (future, start_time)
        self.shutdown = False

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
        print(f"[*] Queues: {', '.join(self.queues)}")
        print(f"[*] Concurrency: {self.concurrency}")
        if self.task_timeout:
            print(f"[*] Task timeout: {self.task_timeout}s")

        try:
            while not self.shutdown:
                self._heartbeat()
                self._check_stuck_tasks()
                self._fetch_and_run()
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[*] Shutting down gracefully...")
            self.shutdown = True
        finally:
            self.pool.shutdown(wait=True)
            with get_conn() as conn:
                conn.execute("DELETE FROM workers WHERE worker_id=?", (self.worker_id,))
            print("[*] Worker stopped.")

    def _check_stuck_tasks(self):
        """Check for stuck tasks and kill them if timeout exceeded"""
        if not self.task_timeout:
            return

        now = time.time()
        stuck_tasks = []

        for task_id, (future, start_time) in list(self.running_tasks.items()):
            elapsed = now - start_time
            if elapsed > self.task_timeout:
                stuck_tasks.append(task_id)
                print(f"[!] Task {task_id} exceeded timeout ({elapsed:.1f}s > {self.task_timeout}s), cancelling...")
                future.cancel()

                # Mark as failed in DB
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE tasks SET status='failed', error=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
                        (f"Task timeout exceeded ({self.task_timeout}s)", task_id),
                    )

        # Remove stuck tasks from tracking
        for task_id in stuck_tasks:
            self.running_tasks.pop(task_id, None)

    def _fetch_and_run(self):
        # Clean up completed tasks
        for task_id, (future, _) in list(self.running_tasks.items()):
            if future.done():
                self.running_tasks.pop(task_id, None)

        # Don't fetch if at capacity
        if len(self.running_tasks) >= self.concurrency:
            return

        with get_conn() as conn:
            q_marks = ",".join(["?"] * len(self.queues))
            row = conn.execute(
                f"""
                UPDATE tasks SET status='running', worker_id=?
                WHERE id = (
                    SELECT id FROM tasks 
                    WHERE status='pending' AND queue IN ({q_marks})
                    AND run_at <= CURRENT_TIMESTAMP
                    ORDER BY priority DESC, id ASC LIMIT 1
                ) RETURNING id, name, payload
            """,
                (self.worker_id, *self.queues),
            ).fetchone()

            if row:
                task_id = row["id"]
                future = self.pool.submit(
                    _run_task_in_thread, task_id, row["name"], row["payload"], self.worker_id, self.task_timeout
                )
                self.running_tasks[task_id] = (future, time.time())
                print(f"[+] Started task {task_id}: {row['name']}")
