from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
from typing import Optional

from liteq.db import set_db_path, init_db
from liteq.monitoring import (
    get_queue_stats,
    get_task_by_id,
    get_failed_tasks,
    list_queues,
    get_active_workers,
    get_recent_tasks,
    get_task_timeline,
    get_worker_performance,
    retry_task,
)
from liteq.control import cancel_task, pause_task, resume_task

app = FastAPI(title="LiteQ Monitor", version="0.1.2")


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/overview")
async def overview():
    stats = get_queue_stats()
    queues = list_queues()
    workers = get_active_workers()

    total_tasks = sum(s["count"] for s in stats)
    total_pending = sum(s["count"] for s in stats if s.get("status") == "pending")
    total_running = sum(s["count"] for s in stats if s.get("status") == "running")
    total_failed = sum(s["count"] for s in stats if s.get("status") == "failed")
    total_done = sum(s["count"] for s in stats if s.get("status") == "done")

    return {
        "total_tasks": total_tasks,
        "total_pending": total_pending,
        "total_running": total_running,
        "total_failed": total_failed,
        "total_done": total_done,
        "total_queues": len(queues),
        "active_workers": len(workers),
        "queues": queues,
    }


@app.get("/api/workers")
async def workers():
    workers_list = get_active_workers()
    performance = get_worker_performance()

    worker_map = {}
    for worker in workers_list:
        worker_id = worker["worker_id"]
        worker_map[worker_id] = {
            "worker_id": worker_id,
            "active_tasks": worker["active_tasks"],
            "last_heartbeat": worker["last_heartbeat"],
            "queues": worker["queues"].split(",") if worker.get("queues") else [],
            "performance": {},
        }

    for perf in performance:
        worker_id = perf["worker_id"]
        if worker_id not in worker_map:
            worker_map[worker_id] = {
                "worker_id": worker_id,
                "active_tasks": 0,
                "last_heartbeat": None,
                "queues": [],
                "performance": {},
            }
        worker_map[worker_id]["performance"][perf["status"]] = {
            "count": perf["task_count"],
            "avg_duration": perf["avg_duration_seconds"],
            "last_finished": perf["last_task_finished"],
        }

    return list(worker_map.values())


@app.get("/api/queues")
async def queues_stats():
    stats = get_queue_stats()
    queues = list_queues()

    queue_map = {q: {} for q in queues}

    for stat in stats:
        queue = stat.get("queue")
        if queue:
            status = stat["status"]
            queue_map[queue][status] = {
                "count": stat["count"],
                "avg_attempts": stat["avg_attempts"],
                "min_priority": stat["min_priority"],
                "max_priority": stat["max_priority"],
            }

    result = []
    for queue, stats in queue_map.items():
        result.append(
            {
                "name": queue,
                "stats": stats,
                "total": sum(s["count"] for s in stats.values()),
            }
        )

    return result


@app.get("/api/tasks")
async def tasks(
    limit: int = 50,
    queue: Optional[str] = None,
    status: Optional[str] = None,
):
    tasks_list = get_recent_tasks(limit=limit, queue=queue, status=status)
    return tasks_list


@app.get("/api/tasks/{task_id}")
async def task_details(task_id: int):
    """Get task details by ID"""
    task = get_task_by_id(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task


@app.get("/api/failed-tasks")
async def failed_tasks(limit: int = 100, queue: Optional[str] = None):
    tasks_list = get_failed_tasks(limit=limit, queue=queue)
    return tasks_list


@app.get("/api/timeline")
async def timeline(hours: int = 24):
    data = get_task_timeline(hours=hours)
    return data


@app.post("/api/tasks/{task_id}/retry")
async def retry_task_endpoint(task_id: int):
    try:
        retry_task(task_id)
        return {"status": "success", "message": f"Task {task_id} queued for retry"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task_endpoint(task_id: int):
    try:
        cancel_task(task_id)
        return {"status": "success", "message": f"Task {task_id} cancelled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


@app.post("/api/tasks/{task_id}/pause")
async def pause_task_endpoint(task_id: int):
    try:
        pause_task(task_id)
        return {"status": "success", "message": f"Task {task_id} paused"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


@app.post("/api/tasks/{task_id}/resume")
async def resume_task_endpoint(task_id: int):
    try:
        resume_task(task_id)
        return {"status": "success", "message": f"Task {task_id} resumed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400


def run_monitor(
    db_path: str = "tasks.db",
    host: str = "127.0.0.1",
    port: int = 5151,
):
    set_db_path(db_path)
    init_db()

    print(f"Starting LiteQ Monitor on http://{host}:{port}")
    print("Press CTRL+C to quit")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_monitor()
