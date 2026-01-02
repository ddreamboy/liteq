# Quick Start Guide

## Installation

### For Users (after publishing to PyPI)
```bash
pip install liteq
```

### For Development
```bash
# Clone the repository
git clone https://github.com/ddreamboy/liteq.git
cd liteq

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## 5-Minute Tutorial

### 1. Define Tasks

```python
# my_tasks.py
from liteq import task

@task(queue='emails', max_retries=3)
async def send_email(to: str, subject: str):
    print(f"Sending to {to}: {subject}")
    # Your email logic here
    
@task(queue='reports')
async def generate_report(report_id: int):
    print(f"Generating report {report_id}")
    # Your report logic here
```

### 2. Start Workers

```python
# worker.py
import asyncio
from liteq import QueueManager

async def main():
    manager = QueueManager()
    manager.initialize()
    
    # Add workers for different queues
    manager.add_worker("worker-1", queues=['emails'])
    manager.add_worker("worker-2", queues=['reports'])
    
    await manager.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Enqueue Tasks

```python
# producer.py
from liteq import enqueue

# Enqueue tasks
enqueue("send_email", {"to": "user@example.com", "subject": "Hello"}, queue='emails')
enqueue("generate_report", {"report_id": 123}, queue='reports')
```

### 4. Run

```bash
# Terminal 1: Start workers
python worker.py

# Terminal 2: Enqueue tasks
python producer.py
```

## Common Patterns

### High Priority Tasks
```python
enqueue("urgent_email", {...}, queue='emails', priority=100)
```

### Delayed Tasks
```python
enqueue("reminder", {...}, delay=3600)  # Run in 1 hour
```

### Batch Enqueue
```python
from liteq import enqueue_many

tasks = [
    {"task_name": "send_email", "payload": {"to": f"user{i}@example.com"}, "queue": "emails"}
    for i in range(100)
]
enqueue_many(tasks)
```

### Monitor Queues
```python
from liteq import get_queue_stats, get_failed_tasks

stats = get_queue_stats(queue='emails')
print(stats)

failed = get_failed_tasks(limit=10)
for task in failed:
    print(task['last_error'])
```

## Need Help?

- [Full Documentation](README.md)
- [Examples](examples/)
- [Report Issues](https://github.com/ddreamboy/liteq/issues)
