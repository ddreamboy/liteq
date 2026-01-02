import signal
import sys
import asyncio
import logging
from recovery import pause_running

logger = logging.getLogger(__name__)

_shutdown_event = None
_workers = []

def setup_signals(workers=None):
    """
    Setup signal handlers for graceful shutdown
    
    Args:
        workers: List of Worker instances to stop gracefully
    """
    global _workers, _shutdown_event
    _workers = workers or []
    _shutdown_event = asyncio.Event()
    
    def handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        
        # Stop workers
        for worker in _workers:
            asyncio.create_task(worker.stop())
        
        # Pause running tasks
        pause_running()
        
        # Set shutdown event
        _shutdown_event.set()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

async def wait_for_shutdown():
    """Wait for shutdown signal"""
    await _shutdown_event.wait()