from db import get_conn

def recover_paused():
    conn = get_conn()
    conn.execute("""
        UPDATE tasks
        SET status='pending'
        WHERE status='paused'
    """)
    conn.commit()


def pause_running():
    conn = get_conn()
    conn.execute("""
        UPDATE tasks
        SET status='paused'
        WHERE status='running'
    """)
    conn.commit()
