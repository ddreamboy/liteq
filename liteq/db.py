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
            started_at DATETIME,
            finished_at DATETIME,
            result TEXT,
            error TEXT,
            timeout INTEGER
        )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            worker_id TEXT PRIMARY KEY,
            hostname TEXT,
            queues TEXT,
            concurrency INTEGER,
            last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            cron_expr TEXT NOT NULL,
            payload TEXT NOT NULL,
            queue TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_run DATETIME,
            next_run DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_fetch ON tasks(status, queue, priority DESC, run_at)")

        # Add columns if they don't exist (migration)
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN started_at DATETIME")
        except:
            pass
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN timeout INTEGER")
        except:
            pass
