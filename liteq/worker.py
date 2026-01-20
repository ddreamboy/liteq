import asyncio
import inspect
import json
import logging
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from .core import TASK_REGISTRY
from .db import get_conn

logger = logging.getLogger(__name__)


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

        # Retry logic with exponential backoff
        with get_conn() as conn:
            task_info = conn.execute("SELECT attempts, max_retries FROM tasks WHERE id=?", (t_id,)).fetchone()

            new_attempts = task_info["attempts"] + 1

            if new_attempts < task_info["max_retries"]:
                # Retry: return to pending with exponential backoff
                retry_delay_seconds = min(300, (2**new_attempts) * 10)  # max 5 min
                run_at = (datetime.now() + timedelta(seconds=retry_delay_seconds)).isoformat()

                conn.execute(
                    "UPDATE tasks SET status='pending', attempts=?, error=?, worker_id=NULL, run_at=? WHERE id=?",
                    (new_attempts, error_msg, run_at, t_id),
                )
                logger.info(
                    f"Task {t_id} failed (attempt {new_attempts}/{task_info['max_retries']}), retrying in {retry_delay_seconds}s"
                )
            else:
                # Final failure
                conn.execute(
                    "UPDATE tasks SET status='failed', attempts=?, error=?, finished_at=CURRENT_TIMESTAMP, worker_id=? WHERE id=?",
                    (new_attempts, error_msg, worker_id, t_id),
                )
                logger.error(f"Task {t_id} failed permanently after {new_attempts} attempts")


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
        logger.info(f"LiteQ Worker {self.worker_id} started")
        logger.info(f"Queues: {', '.join(self.queues)}")
        logger.info(f"Concurrency: {self.concurrency}")
        if self.task_timeout:
            logger.info(f"Task timeout: {self.task_timeout}s")

        try:
            while not self.shutdown:
                self._heartbeat()
                self._check_stuck_tasks()
                self._fetch_and_run()
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            self.shutdown = True
        finally:
            self.pool.shutdown(wait=True)
            with get_conn() as conn:
                conn.execute("DELETE FROM workers WHERE worker_id=?", (self.worker_id,))
            logger.info("Worker stopped")

    def _check_stuck_tasks(self):
        """
        Check for stuck tasks and mark them as failed if timeout exceeded.

        Note: future.cancel() does NOT interrupt already running threads.
        This method only marks tasks as failed in the database if they exceed
        the timeout threshold. The actual thread will continue running until
        completion. For true task interruption, use ProcessPoolExecutor instead.
        """
        if not self.task_timeout:
            return

        now = time.time()
        stuck_tasks = []

        for task_id, (future, start_time) in list(self.running_tasks.items()):
            elapsed = now - start_time
            if elapsed > self.task_timeout:
                stuck_tasks.append(task_id)
                logger.warning(f"Task {task_id} exceeded timeout ({elapsed:.1f}s > {self.task_timeout}s)")

                # Note: cancel() won't stop already running thread, only prevents it from starting
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
            # Use BEGIN IMMEDIATE to prevent race conditions between multiple workers
            conn.execute("BEGIN IMMEDIATE")
            try:
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
                    logger.info(f"Started task {task_id}: {row['name']}")

                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error fetching task: {e}")
