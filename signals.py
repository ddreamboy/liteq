import signal
import sys
from recovery import pause_running

def setup_signals():
    def handler(sig, frame):
        pause_running()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
