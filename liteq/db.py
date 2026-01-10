import os
import sqlite3

DB_PATH = os.environ.get("LITEQ_DB", "liteq.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            queue TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            worker_id TEXT,
            run_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME,
            result TEXT,
            error TEXT
        )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            worker_id TEXT PRIMARY KEY,
            hostname TEXT,
            queues TEXT,
            concurrency INTEGER,
            last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fetch ON tasks(status, queue, priority DESC, run_at)"
        )
