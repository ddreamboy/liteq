import asyncio
from decorators import task
from producer import enqueue
from worker import worker
from db import init_db
from recovery import recover_paused
from signals import setup_signals

@task(max_retries=3)
async def hello(name: str):
    print("Hello", name)
    await asyncio.sleep(1)

async def main():
    init_db()
    recover_paused()
    setup_signals()

    enqueue("hello", {"name": "Jemma"}, delay=2)

    await worker("worker-1")

asyncio.run(main())
