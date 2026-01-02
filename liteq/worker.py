import asyncio
import json
import traceback
import logging
from inspect import iscoroutinefunction
from typing import List
from liteq.db import get_conn, get_db_transaction
from liteq.registry import get_task

POLL_INTERVAL = 1
logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        worker_id: str,
        queues: List[str] = None,
        poll_interval: int = POLL_INTERVAL,
    ):
        """
        Create a worker instance

        Args:
            worker_id: Unique identifier for this worker
            queues: List of queue names to process (default: ['default'])
            poll_interval: Polling interval in seconds
        """
        self.worker_id = worker_id
        self.queues = queues or ["default"]
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        """Start the worker"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started, listening to queues: {self.queues}")

        while self.running:
            try:
                await self._process_next_task()
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Gracefully stop the worker"""
        logger.info(f"Worker {self.worker_id} stopping...")
        self.running = False

    async def _process_next_task(self):
        """Process the next available task from assigned queues"""
        conn = get_conn()

        # Build queue filter
        queue_placeholders = ",".join("?" * len(self.queues))

        task = conn.execute(
            f"""
            SELECT * FROM tasks
            WHERE status='pending'
              AND queue IN ({queue_placeholders})
              AND run_at <= CURRENT_TIMESTAMP
            ORDER BY priority DESC, id ASC
            LIMIT 1
        """,
            self.queues,
        ).fetchone()

        if not task:
            await asyncio.sleep(self.poll_interval)
            return

        # Atomic task claim
        with get_db_transaction() as conn:
            updated = conn.execute(
                """
                UPDATE tasks
                SET status='running',
                    worker_id=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='pending'
            """,
                (self.worker_id, task["id"]),
            ).rowcount

        if updated == 0:
            # Task already claimed by another worker
            return

        await self._execute_task(task)

    async def _execute_task(self, task):
        """Execute a single task"""
        conn = get_conn()

        try:
            func = get_task(task["name"])
            if func is None:
                raise ValueError(f"Task '{task['name']}' not found in registry")

            payload = json.loads(task["payload"])

            # Support for synchronous and asynchronous tasks
            if iscoroutinefunction(func):
                result = await func(**payload)
            else:
                # Run synchronous function in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(**payload))

            with get_db_transaction() as conn:
                conn.execute(
                    """
                    UPDATE tasks
                    SET status='done',
                        updated_at=CURRENT_TIMESTAMP,
                        completed_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """,
                    (task["id"],),
                )

            logger.info(
                f"Task {task['id']} ({task['name']}) from queue '{task['queue']}' completed successfully"
            )

        except Exception as e:
            attempts = task["attempts"] + 1
            tb = traceback.format_exc()
            logger.error(f"Task {task['id']} failed (attempt {attempts}): {e}")

            with get_db_transaction() as conn:
                if attempts >= task["max_retries"]:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET status='failed',
                            attempts=?,
                            last_error=?,
                            updated_at=CURRENT_TIMESTAMP,
                            completed_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """,
                        (attempts, tb, task["id"]),
                    )
                else:
                    # Exponential backoff: 5, 10, 20 secs
                    delay = min(5 * (2 ** (attempts - 1)), 300)
                    conn.execute(
                        """
                        UPDATE tasks
                        SET status='pending',
                            attempts=?,
                            run_at=datetime('now', '+{} seconds'),
                            last_error=?,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """.format(delay),
                        (attempts, tb, task["id"]),
                    )
