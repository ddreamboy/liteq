import sqlite3
from contextlib import contextmanager
from threading import local

DB_PATH = 'tasks.db'

_thread_local = local()

def get_conn():
    if not hasattr(_thread_local, 'conn'):
        _thread_local.conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        _thread_local.conn.row_factory = sqlite3.Row
        _thread_local.conn.execute("PRAGMA journal_mode=WAL")
        _thread_local.conn.execute("PRAGMA busy_timeout=30000")
    return _thread_local.conn


@contextmanager
def get_db_transaction():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        payload TEXT,
        status TEXT CHECK(status IN (
            'pending', 'running', 'paused', 'done', 'failed'
        )) NOT NULL DEFAULT 'pending',
        run_at DATETIME NOT NULL,
        attempts INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        last_error TEXT,
        priority INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        completed_at DATETIME,
        worker_id TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_tasks_run
        ON tasks(status, run_at, priority DESC);
    
    CREATE INDEX IF NOT EXISTS idx_tasks_name
        ON tasks(name);
    
    CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks(status);
    """)
    conn.commit()