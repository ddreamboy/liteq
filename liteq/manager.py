import asyncio
import logging
from typing import List, Dict, Optional
from liteq.db import init_db, set_db_path
from liteq.worker import Worker
from liteq.recovery import recover_paused, recover_stuck_tasks, recover_retry_tasks
from liteq.signals import setup_signals
from liteq.monitoring import get_queue_stats, get_pending_count
from liteq.watchdog import Watchdog

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manager for coordinating multiple workers and queues
    """

    def __init__(
        self,
        db_path: str = "tasks.db",
        enable_watchdog: bool = True,
        watchdog_lease_timeout: int = 60,
        watchdog_check_interval: int = 30,
    ):
        """
        Initialize the queue manager

        Args:
            db_path: Path to SQLite database
            enable_watchdog: Enable watchdog for stuck task recovery
            watchdog_lease_timeout: Seconds before a task is considered stuck
            watchdog_check_interval: How often watchdog checks for stuck tasks
        """
        self.db_path = db_path
        self.workers: List[Worker] = []
        self.worker_tasks = []
        self._initialized = False
        self.enable_watchdog = enable_watchdog
        self.watchdog: Optional[Watchdog] = None
        self.watchdog_task = None
        self.watchdog_lease_timeout = watchdog_lease_timeout
        self.watchdog_check_interval = watchdog_check_interval

    def initialize(self, recover_stuck_timeout_minutes: int = 5):
        """Initialize the database and recover tasks

        Args:
            recover_stuck_timeout_minutes: Minutes before a task is considered stuck (default: 5)
        """
        if not self._initialized:
            set_db_path(self.db_path)
            init_db()
            recover_paused()
            recover_retry_tasks()
            recover_stuck_tasks(timeout_minutes=recover_stuck_timeout_minutes)
            self._initialized = True
            logger.info(f"QueueManager initialized with database: {self.db_path}")

    def add_worker(self, worker_id: str, queues: List[str] = None, poll_interval: int = 1):
        """
        Add a worker to the manager

        Args:
            worker_id: Unique worker identifier
            queues: List of queue names this worker should process
            poll_interval: Polling interval in seconds

        Returns:
            Worker instance
        """
        worker = Worker(worker_id, queues=queues, poll_interval=poll_interval)
        self.workers.append(worker)
        logger.info(f"Added worker '{worker_id}' for queues: {queues or ['default']}")
        return worker

    def remove_worker(self, worker_id: str):
        """
        Remove a worker from the manager

        Args:
            worker_id: Worker identifier to remove
        """
        self.workers = [w for w in self.workers if w.worker_id != worker_id]
        logger.info(f"Removed worker '{worker_id}'")

    async def start(self, setup_signal_handlers: bool = True):
        """
        Start all workers

        Args:
            setup_signal_handlers: Whether to setup signal handlers for graceful shutdown
        """
        if not self._initialized:
            self.initialize()

        if not self.workers:
            logger.warning("No workers added to manager")
            return

        if setup_signal_handlers:
            setup_signals(self.workers)

        # Start watchdog if enabled
        if self.enable_watchdog:
            self.watchdog = Watchdog(
                lease_timeout_seconds=self.watchdog_lease_timeout,
                check_interval_seconds=self.watchdog_check_interval,
            )
            self.watchdog_task = asyncio.create_task(self.watchdog.start())
            logger.info("Watchdog started")

        logger.info(f"Starting {len(self.workers)} workers...")
        self.worker_tasks = [asyncio.create_task(w.start()) for w in self.workers]

        try:
            # Gather all tasks including watchdog
            all_tasks = self.worker_tasks.copy()
            if self.watchdog_task:
                all_tasks.append(self.watchdog_task)
            await asyncio.gather(*all_tasks)
        except asyncio.CancelledError:
            logger.info("Workers cancelled")
            await self.stop()

    async def stop(self):
        """Stop all workers gracefully"""
        logger.info("Stopping all workers...")

        # Stop watchdog
        if self.watchdog:
            await self.watchdog.stop()
            if self.watchdog_task and not self.watchdog_task.done():
                self.watchdog_task.cancel()
                try:
                    await self.watchdog_task
                except asyncio.CancelledError:
                    pass

        # Stop workers
        stop_tasks = [w.stop() for w in self.workers]
        await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Cancel worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        logger.info("All workers stopped")

    def get_stats(self, queue: str = None) -> List[Dict]:
        """
        Get queue statistics

        Args:
            queue: Specific queue name (None = all queues)

        Returns:
            List of statistics dictionaries
        """
        return get_queue_stats(queue)

    def get_pending_count(self, queue: str = None) -> int:
        """
        Get count of pending tasks

        Args:
            queue: Specific queue name (None = all queues)

        Returns:
            Number of pending tasks
        """
        return get_pending_count(queue)

    def __repr__(self):
        return f"<QueueManager workers={len(self.workers)} db={self.db_path}>"
