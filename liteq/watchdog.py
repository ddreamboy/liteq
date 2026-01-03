import asyncio
import logging
from liteq.db import get_db_transaction

logger = logging.getLogger(__name__)


class Watchdog:
    """
    Watchdog process that monitors running tasks and recovers stuck ones

    Checks for:
    - Tasks with outdated heartbeat (worker likely crashed)
    - Tasks running for too long
    """

    def __init__(
        self,
        lease_timeout_seconds: int = 60,
        check_interval_seconds: int = 30,
    ):
        """
        Initialize watchdog

        Args:
            lease_timeout_seconds: Seconds before a task is considered stuck
            check_interval_seconds: How often to check for stuck tasks
        """
        self.lease_timeout = lease_timeout_seconds
        self.check_interval = check_interval_seconds
        self.running = False

    async def start(self):
        """Start the watchdog loop"""
        self.running = True
        logger.info(
            f"Watchdog started (lease_timeout={self.lease_timeout}s, "
            f"check_interval={self.check_interval}s)"
        )

        while self.running:
            try:
                await self._check_stuck_tasks()
            except Exception as e:
                logger.error(f"Watchdog error: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the watchdog"""
        logger.info("Watchdog stopping...")
        self.running = False

    async def _check_stuck_tasks(self):
        """Check for and recover stuck tasks"""
        with get_db_transaction() as conn:
            # Find tasks with outdated heartbeat
            result = conn.execute(
                """
                UPDATE tasks
                SET status='retry',
                    worker_id=NULL,
                    retry_at=datetime('now', '+5 seconds'),
                    updated_at=CURRENT_TIMESTAMP
                WHERE status='running'
                  AND (
                    heartbeat_at IS NULL
                    OR heartbeat_at < datetime('now', '-{} seconds')
                  )
                """.format(self.lease_timeout)
            )

            recovered_count = result.rowcount

        if recovered_count > 0:
            logger.warning(
                f"Watchdog recovered {recovered_count} stuck tasks "
                f"(heartbeat timeout: {self.lease_timeout}s)"
            )


async def run_watchdog(lease_timeout_seconds: int = 60, check_interval_seconds: int = 30):
    """
    Convenience function to run watchdog

    Args:
        lease_timeout_seconds: Seconds before a task is considered stuck
        check_interval_seconds: How often to check for stuck tasks
    """
    watchdog = Watchdog(lease_timeout_seconds, check_interval_seconds)
    await watchdog.start()
