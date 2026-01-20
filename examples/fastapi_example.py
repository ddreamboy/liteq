"""
FastAPI integration example for LiteQ

Run this example:
1. Install dependencies: pip install fastapi uvicorn
2. Start the API: uvicorn examples.fastapi_example:app --reload
3. Start worker: liteq worker --app examples/fastapi_example.py --timeout 300
4. Visit: http://localhost:8000/docs
"""

import asyncio
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from liteq import task
from liteq.db import init_db
from liteq.fastapi import LiteQBackgroundTasks, enqueue_task

# Initialize database
init_db()

app = FastAPI(title="LiteQ + FastAPI Example")


# Define tasks
@task(queue="emails", timeout=60)
async def send_email(to: str, subject: str, body: str):
    """Simulated email sending task"""
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(2)  # Simulate email sending
    print(f"Email sent to {to}")
    return {"status": "sent", "to": to, "timestamp": datetime.now().isoformat()}


@task(queue="processing", timeout=300)
def process_data(data: dict):
    """Heavy data processing task"""
    print(f"Processing data: {data}")
    time.sleep(5)  # Simulate heavy processing
    result = {"processed": True, "items": len(data.get("items", []))}
    print(f"Processing complete: {result}")
    return result


@task(queue="reports", timeout=600)
async def generate_report(report_type: str, user_id: int):
    """Generate report task"""
    print(f"Generating {report_type} report for user {user_id}")
    await asyncio.sleep(10)  # Simulate report generation
    return {"report_type": report_type, "user_id": user_id, "generated_at": datetime.now().isoformat()}


# API Models
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str


class DataRequest(BaseModel):
    items: list
    user_id: Optional[int] = None


# API Endpoints


@app.get("/")
async def root():
    return {
        "message": "LiteQ + FastAPI Integration",
        "docs": "/docs",
        "examples": {
            "send_email": "POST /send-email",
            "process_data": "POST /process-data",
            "generate_report": "POST /generate-report/{report_type}",
        },
    }


@app.post("/send-email")
async def api_send_email(email: EmailRequest):
    """
    Enqueue email sending task using .delay()

    This is the simplest way to use LiteQ with FastAPI.
    """
    task_id = send_email.delay(email.to, email.subject, email.body)
    return {"message": "Email queued for sending", "task_id": task_id}


@app.post("/send-email-helper")
async def api_send_email_helper(email: EmailRequest):
    """
    Enqueue email using enqueue_task helper function.

    Alternative way using helper function.
    """
    task_id = enqueue_task(send_email, email.to, email.subject, email.body)
    return {"message": "Email queued for sending", "task_id": task_id}


@app.post("/send-email-background")
async def api_send_email_background(email: EmailRequest, background: LiteQBackgroundTasks):
    """
    Use LiteQBackgroundTasks (FastAPI-like interface).

    This mimics FastAPI's BackgroundTasks but uses LiteQ.
    """
    background.add_task(send_email, email.to, email.subject, email.body)
    return {"message": "Email queued for sending"}


@app.post("/process-data")
async def api_process_data(data: DataRequest):
    """Enqueue data processing task"""
    task_id = process_data.delay(data.dict())
    return {"message": "Data processing started", "task_id": task_id}


@app.post("/generate-report/{report_type}")
async def api_generate_report(report_type: str, user_id: int = 1):
    """Enqueue report generation task"""
    task_id = generate_report.delay(report_type, user_id)
    return {"message": f"{report_type} report generation started", "task_id": task_id, "user_id": user_id}


@app.get("/task/{task_id}")
async def get_task_status(task_id: int):
    """Check task status"""
    from liteq.db import get_conn

    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

        if not task:
            return {"error": "Task not found"}

        return dict(task)


if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI server...")
    print("API docs: http://localhost:8000/docs")
    print("\nDon't forget to start worker:")
    print("  liteq worker --app examples/fastapi_example.py --timeout 300")
    uvicorn.run(app, host="0.0.0.0", port=8000)
