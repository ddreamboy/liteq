"""Example: FastAPI with task status checking"""

import time

from fastapi import FastAPI

from liteq import task
from liteq.db import init_db
from liteq.fastapi import LiteQBackgroundTasks

app = FastAPI()

# Initialize database
init_db()


@task(queue="emails", timeout=60)
def send_email(to: str, subject: str, body: str):
    """Simulate sending email"""
    time.sleep(2)  # Simulate email sending
    print(f"Sending email to {to}: {subject}")
    return {"sent": True, "to": to, "timestamp": time.time()}


@task(queue="reports")
def generate_report(user_id: int, report_type: str):
    """Simulate report generation"""
    time.sleep(5)  # Simulate processing
    print(f"Generating {report_type} report for user {user_id}")
    return {"user_id": user_id, "report_type": report_type, "url": f"/reports/{user_id}/{report_type}.pdf"}


@app.post("/send-email")
async def create_email_task(to: str, subject: str, body: str):
    """Enqueue email sending task and return task_id"""
    background = LiteQBackgroundTasks(queue="emails")
    task_id = background.add_task(send_email, to, subject, body)

    return {"message": "Email queued for sending", "task_id": task_id}


@app.post("/generate-report")
async def create_report_task(user_id: int, report_type: str):
    """Enqueue report generation task"""
    background = LiteQBackgroundTasks(queue="reports")
    task_id = background.add_task(generate_report, user_id, report_type)

    return {"message": "Report generation started", "task_id": task_id, "status_url": f"/tasks/{task_id}"}


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: int):
    """Check task status by ID"""
    from liteq import get_task_status

    status = get_task_status(task_id)

    if not status:
        return {"error": "Task not found"}, 404

    response = {
        "task_id": status["id"],
        "status": status["status"],
        "queue": status["queue"],
        "attempts": status["attempts"],
        "max_retries": status["max_retries"],
        "created_at": status["created_at"],
    }

    if status["status"] == "done":
        response["result"] = status["result"]
        response["finished_at"] = status["finished_at"]
    elif status["status"] == "failed":
        response["error"] = status["error"]
        response["finished_at"] = status["finished_at"]
    elif status["status"] == "running":
        response["worker_id"] = status["worker_id"]
        response["started_at"] = status["started_at"]

    return response


@app.post("/batch-emails")
async def batch_send_emails(recipients: list[str], subject: str, body: str):
    """Send emails to multiple recipients and return all task IDs"""
    background = LiteQBackgroundTasks(queue="emails")

    # Enqueue multiple tasks
    for recipient in recipients:
        background.add_task(send_email, recipient, subject, body)

    return {
        "message": f"Queued {len(recipients)} emails",
        "task_ids": background.task_ids,
        "status_url": "/batch-status",
    }


@app.post("/batch-status")
async def check_batch_status(task_ids: list[int]):
    """Check status of multiple tasks"""
    from liteq import get_task_status

    statuses = []
    for task_id in task_ids:
        status = get_task_status(task_id)
        if status:
            statuses.append({"task_id": status["id"], "status": status["status"], "attempts": status["attempts"]})

    summary = {
        "total": len(statuses),
        "pending": sum(1 for s in statuses if s["status"] == "pending"),
        "running": sum(1 for s in statuses if s["status"] == "running"),
        "done": sum(1 for s in statuses if s["status"] == "done"),
        "failed": sum(1 for s in statuses if s["status"] == "failed"),
    }

    return {"summary": summary, "tasks": statuses}


if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI server with LiteQ...")
    print("\nAPI Endpoints:")
    print("  POST /send-email - Queue single email")
    print("  POST /generate-report - Queue report generation")
    print("  POST /batch-emails - Queue multiple emails")
    print("  GET  /tasks/{task_id} - Check task status")
    print("  POST /batch-status - Check multiple tasks status")
    print("\nTo process tasks, run in another terminal:")
    print("  liteq worker --app examples/fastapi_check_status.py --queues emails,reports")
    print()

    uvicorn.run(app, host="127.0.0.1", port=8000)
