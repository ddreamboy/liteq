import asyncio
import json
import traceback
import logging
from inspect import iscoroutinefunction, signature
from typing import List
from liteq.db import get_conn, get_db_transaction
from liteq.registry import get_task
from liteq.context import TaskContext

POLL_INTERVAL = 1
HEARTBEAT_INTERVAL = 10  # seconds
logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        worker_id: str,
        queues: List[str] = None,
        poll_interval: int = POLL_INTERVAL,
        heartbeat_interval: int = HEARTBEAT_INTERVAL,
    ):
        """
        Create a worker instance

        Args:
            worker_id: Unique identifier for this worker
            queues: List of queue names to process (default: ['default'])
            poll_interval: Polling interval in seconds
            heartbeat_interval: Heartbeat update interval in seconds
        """
        self.worker_id = worker_id
        self.queues = queues or ["default"]
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.running = False
        self._shutdown_requested = False
        self._current_task_id = None

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
        self._shutdown_requested = True
        self.running = False

    async def _process_next_task(self):
        """Process the next available task from assigned queues"""
        # Don't accept new tasks if shutdown requested
        if self._shutdown_requested:
            await asyncio.sleep(self.poll_interval)
            return

        conn = get_conn()

        # Build queue filter
        queue_placeholders = ",".join("?" * len(self.queues))

        # First, try to get pending or retry tasks that are ready
        task = conn.execute(
            f"""
            SELECT * FROM tasks
            WHERE status IN ('pending', 'retry')
              AND queue IN ({queue_placeholders})
              AND run_at <= CURRENT_TIMESTAMP
              AND (retry_at IS NULL OR retry_at <= CURRENT_TIMESTAMP)
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
                    heartbeat_at=CURRENT_TIMESTAMP,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status IN ('pending', 'retry')
            """,
                (self.worker_id, task["id"]),
            ).rowcount

        if updated == 0:
            # Task already claimed by another worker
            return

        self._current_task_id = task["id"]
        await self._execute_task(task)
        self._current_task_id = None

    async def _execute_task(self, task):
        """Execute a single task"""
        conn = get_conn()
        heartbeat_task = None

        try:
            func = get_task(task["name"])
            if func is None:
                raise ValueError(f"Task '{task['name']}' not found in registry")

            payload = json.loads(task["payload"])

            # Create task context
            ctx = TaskContext(task["id"], dict(task))

            # Check if function accepts context
            sig = signature(func)
            accepts_context = "ctx" in sig.parameters or "context" in sig.parameters

            # Start heartbeat background task
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(task["id"]))

            # Support for synchronous and asynchronous tasks
            if iscoroutinefunction(func):
                if accepts_context:
                    result = await func(ctx=ctx, **payload)
                else:
                    result = await func(**payload)
            else:
                # Run synchronous function in executor
                loop = asyncio.get_event_loop()
                if accepts_context:
                    result = await loop.run_in_executor(None, lambda: func(ctx=ctx, **payload))
                else:
                    result = await loop.run_in_executor(None, lambda: func(**payload))

            # Cancel heartbeat
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            with get_db_transaction() as conn:
                conn.execute(
                    """
                    UPDATE tasks
                    SET status='done',
                        result=?,
                        updated_at=CURRENT_TIMESTAMP,
                        finished_at=CURRENT_TIMESTAMP,
                        completed_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """,
                    (
                        json.dumps(result) if result is not None else None,
                        task["id"],
                    ),
                )

            logger.info(
                f"Task {task['id']} ({task['name']}) from queue '{task['queue']}' completed successfully"
            )

        except Exception as e:
            # Cancel heartbeat
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            attempts = task["attempts"] + 1
            tb = traceback.format_exc()
            error_msg = str(e)
            logger.error(f"Task {task['id']} failed (attempt {attempts}): {e}")

            with get_db_transaction() as conn:
                max_attempts = task.get("max_attempts") or task.get("max_retries", 3)

                if attempts >= max_attempts:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET status='failed',
                            attempts=?,
                            last_error=?,
                            error_message=?,
                            error_traceback=?,
                            updated_at=CURRENT_TIMESTAMP,
                            finished_at=CURRENT_TIMESTAMP,
                            completed_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """,
                        (attempts, tb, error_msg, tb, task["id"]),
                    )
                else:
                    # Exponential backoff: 5, 10, 20 secs
                    delay = min(5 * (2 ** (attempts - 1)), 300)
                    conn.execute(
                        """
                        UPDATE tasks
                        SET status='retry',
                            attempts=?,
                            retry_at=datetime('now', '+{} seconds'),
                            last_error=?,
                            error_message=?,
                            error_traceback=?,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """.format(delay),
                        (attempts, tb, error_msg, tb, task["id"]),
                    )

    async def _heartbeat_loop(self, task_id: int):
        """Background task to update heartbeat periodically"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                with get_db_transaction() as conn:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET heartbeat_at=CURRENT_TIMESTAMP,
                            updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                        """,
                        (task_id,),
                    )

                logger.debug(f"Heartbeat updated for task {task_id}")
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat loop cancelled for task {task_id}")
            raise
