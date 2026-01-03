import json
import logging
from typing import Any, Dict, Optional
from liteq.db import get_conn, get_db_transaction

logger = logging.getLogger(__name__)


class TaskContext:
    """
    Context object passed to task functions for long-running task support

    Provides:
    - task_id: Stable task identifier
    - Checkpoint/progress management
    - Cancellation checks
    - Heartbeat updates
    """

    def __init__(self, task_id: int, task_data: Dict[str, Any]):
        self.task_id = task_id
        self._task_data = task_data
        self._conn = get_conn()

    @property
    def cancelled(self) -> bool:
        """Check if task cancellation was requested"""
        row = self._conn.execute(
            "SELECT cancel_requested FROM tasks WHERE id=?", (self.task_id,)
        ).fetchone()
        return bool(row and row["cancel_requested"])

    @property
    def paused(self) -> bool:
        """Check if task pause was requested"""
        row = self._conn.execute(
            "SELECT paused_requested FROM tasks WHERE id=?", (self.task_id,)
        ).fetchone()
        return bool(row and row["paused_requested"])

    def save_progress(self, step: str, payload: Optional[Dict[str, Any]] = None):
        """
        Save task progress checkpoint

        Args:
            step: Current step identifier
            payload: Optional progress data
        """
        progress_data = {"step": step, "payload": payload or {}}

        with get_db_transaction() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET progress=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (json.dumps(progress_data), self.task_id),
            )

        logger.debug(f"Task {self.task_id} progress saved: {step}")

    def load_progress(self) -> Optional[Dict[str, Any]]:
        """
        Load saved task progress

        Returns:
            Progress data or None if no progress saved
        """
        row = self._conn.execute(
            "SELECT progress FROM tasks WHERE id=?", (self.task_id,)
        ).fetchone()

        if row and row["progress"]:
            return json.loads(row["progress"])
        return None

    def save_result(self, result: Any):
        """
        Save task result

        Args:
            result: Task result (will be JSON-serialized)
        """
        with get_db_transaction() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET result=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (json.dumps(result), self.task_id),
            )

        logger.debug(f"Task {self.task_id} result saved")

    def update_heartbeat(self):
        """Update task heartbeat timestamp"""
        with get_db_transaction() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET heartbeat_at=CURRENT_TIMESTAMP,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (self.task_id,),
            )
