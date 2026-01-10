import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .db import get_conn, init_db
from .monitoring import (
    get_failed_tasks,
    get_queue_stats,
    get_recent_tasks,
    list_queues,
)

app = FastAPI(title="LiteQ Monitor")

# Путь к шаблонам
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/overview")
async def overview():
    stats = get_queue_stats()

    total_pending = sum(s["count"] for s in stats if s["status"] == "pending")
    total_running = sum(s["count"] for s in stats if s["status"] == "running")
    total_failed = sum(s["count"] for s in stats if s["status"] == "failed")
    total_done = sum(s["count"] for s in stats if s["status"] == "done")

    queues = list_queues()

    return {
        "total_pending": total_pending,
        "total_running": total_running,
        "total_failed": total_failed,
        "total_done": total_done,
        "total_queues": len(queues),
        "active_workers": "N/A",
    }


@app.get("/api/tasks")
async def tasks(limit: int = 50):
    return get_recent_tasks(limit)


@app.get("/api/failed-tasks")
async def failed():
    return get_failed_tasks()


@app.get("/api/queues")
async def queues_info():
    stats = get_queue_stats()
    return stats


@app.post("/api/tasks/{task_id}/retry")
async def retry(task_id: int):
    """Сброс задачи обратно в очередь"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status='pending', attempts=0, error=NULL, run_at=CURRENT_TIMESTAMP WHERE id=?",
            (task_id,),
        )
    return {"status": "success"}


@app.post("/api/tasks/{task_id}/cancel")
async def cancel(task_id: int):
    """Убийство задачи"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status='failed', error='Cancelled by user' WHERE id=?",
            (task_id,),
        )
    return {"status": "success"}


@app.get("/api/workers")
async def workers():
    from .monitoring import get_active_workers

    return get_active_workers()


def run_monitor(host="127.0.0.1", port=5151):
    init_db()
    print(f"[*] LiteQ Monitor UI: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="error")
