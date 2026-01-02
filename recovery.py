import logging
from db import get_db_transaction

logger = logging.getLogger(__name__)

def recover_paused():
    """Recover paused tasks back to pending state"""
    with get_db_transaction() as conn:
        result = conn.execute("""
            UPDATE tasks
            SET status='pending',
                worker_id=NULL
            WHERE status='paused'
        """)
        count = result.rowcount
    
    if count > 0:
        logger.info(f"Recovered {count} paused tasks")

def pause_running():
    """Pause all running tasks"""
    with get_db_transaction() as conn:
        result = conn.execute("""
            UPDATE tasks
            SET status='paused'
            WHERE status='running'
        """)
        count = result.rowcount
    
    if count > 0:
        logger.info(f"Paused {count} running tasks")

def recover_stuck_tasks(timeout_minutes=30):
    """
    Recover tasks that have been running for too long
    """
    with get_db_transaction() as conn:
        result = conn.execute("""
            UPDATE tasks
            SET status='pending',
                worker_id=NULL
            WHERE status='running'
              AND updated_at < datetime('now', '-{} minutes')
        """.format(timeout_minutes))
        count = result.rowcount
    
    if count > 0:
        logger.warning(f"Recovered {count} stuck tasks")
    
    return count

def cleanup_old_tasks(days=30):
    """Delete completed/failed tasks older than specified days"""
    with get_db_transaction() as conn:
        result = conn.execute("""
            DELETE FROM tasks
            WHERE status IN ('done', 'failed')
              AND completed_at < datetime('now', '-{} days')
        """.format(days))
        count = result.rowcount
    
    if count > 0:
        logger.info(f"Cleaned up {count} old tasks")
    
    return count