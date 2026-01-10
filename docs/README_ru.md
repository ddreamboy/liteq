У# LiteQ

<p align="center">
  <a href="https://github.com/ddreamboy/liteq/actions/workflows/tests.yml"><img src="https://github.com/ddreamboy/liteq/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://codecov.io/gh/ddreamboy/liteq"><img src="https://codecov.io/gh/ddreamboy/liteq/branch/master/graph/badge.svg" alt="codecov"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <b>Read in:</b> <a href="../README.md">🇬🇧 English</a>
</p>

Легковесная и быстрая очередь задач для Python, которой не нужны внешние зависимости.

Устали от сложной инфраструктуры? LiteQ — это очередь сообщений на чистом Python и SQLite. Идеально для фоновых задач, job-очередей и асинхронных воркфлоу. Никакого Redis, RabbitMQ или Celery — всё просто работает из коробки.

## Что умеет

- **Ноль зависимостей** — только Python 3.10+ и встроенный SQLite
- **Async и sync вместе** — пишите задачи как `async def` или обычные функции
- **Несколько очередей** — разделяйте типы задач логически
- **Приоритеты** — важные задачи обрабатываются первыми
- **Автоматические повторы** — ретраи с экспоненциальной задержкой при ошибках
- **Масштабирование воркерами** — запускайте сколько угодно обработчиков
- **Длительные задачи** — отслеживайте прогресс, ставьте на паузу, отменяйте
- **Мониторинг из коробки** — статистика очередей и состояние задач
- **Graceful shutdown** — корректная остановка по сигналам без потери данных
- **Всё сохраняется** — SQLite гарантирует, что ничего не потеряется

## Установка

```bash
pip install liteq
```

## Быстрый старт

### Простой пример

```python
import asyncio
from liteq import task, QueueManager

@task(max_retries=3, queue='emails')
async def send_email(to: str, subject: str):
    print(f"Отправляем письмо {to}: {subject}")
    await asyncio.sleep(1)

async def main():
    manager = QueueManager()
    manager.initialize()
    
    manager.add_worker("worker-1", queues=['emails'])
    
    from liteq import enqueue
    enqueue(
        "send_email",
        {"to": "user@example.com", "subject": "Привет!"},
        queue='emails'
    )
    
    await manager.start()

asyncio.run(main())
```

---

### Работа с несколькими очередями
```python
import asyncio
from liteq import task, QueueManager, enqueue

@task(queue='emails', max_retries=3)
async def send_email(to: str, subject: str):
    await asyncio.sleep(1)

@task(queue='reports', max_retries=5)
async def generate_report(report_id: int):
    await asyncio.sleep(2)

@task(queue='notifications', max_retries=2)
def send_sms(phone: str, message: str):
    import time
    time.sleep(0.5)

async def main():
    manager = QueueManager(db_path='myapp.db')
    manager.initialize()
    
    manager.add_worker("worker-1", queues=['emails', 'notifications'])
    manager.add_worker("worker-2", queues=['reports'])
    manager.add_worker("worker-3", queues=['emails', 'reports', 'notifications'])
    
    enqueue("send_email", {"to": "user@example.com", "subject": "Добро пожаловать"}, queue='emails')
    enqueue("generate_report", {"report_id": 123}, queue='reports', priority=10)
    enqueue("send_sms", {"phone": "+1234567890", "message": "Привет"}, queue='notifications')
    
    await manager.start()

asyncio.run(main())
```

---

### Массовое добавление
```python
from liteq import enqueue_many

tasks = [
    {"task_name": "send_email", "payload": {"to": "user1@example.com", "subject": "Привет"}, "queue": "emails"},
    {"task_name": "send_email", "payload": {"to": "user2@example.com", "subject": "Привет"}, "queue": "emails"},
    {"task_name": "generate_report", "payload": {"report_id": 456}, "queue": "reports", "priority": 5},
]

task_ids = enqueue_many(tasks)
print(f"Добавлено задач: {len(task_ids)}")
```

---

### Задачи с приоритетами
```python
from liteq import enqueue

enqueue("send_email", {"to": "vip@example.com", "subject": "Срочно"}, priority=100)
enqueue("send_email", {"to": "user@example.com", "subject": "Обычное"}, priority=10)
# Чем выше приоритет — тем раньше выполнится
enqueue("send_email", {"to": "vip@example.com", "subject": "Срочно"}, priority=100)
enqueue("send_email", {"to": "user@example.com", "subject": "Обычное письмо"}, priority=10)
enqueue("send_email", {"to": "bulk@example.com", "subject": "Рассылка"}, priority=1)
```

### Отложенный запуск
```python
from liteq import enqueue

enqueue("send_reminder", {"user_id": 123}, delay=60)
enqueue("cleanup_temp_files", {}, delay=3600)
```
# Запустится через минуту
```python
enqueue("send_reminder", {"user_id": 123}, delay=60)

# Запустится через час
enqueue("cleanup_temp_files", {}, delay=3600)
```

## Мониторинг

### Веб-интерфейс (как Flower) 🚀

LiteQ включает красивый веб-интерфейс для мониторинга воркеров и задач в реальном времени:

```bash
# Установить зависимости для веб-интерфейса
pip install liteq[web]

# Запустить UI мониторинга
liteq monitor

# Или с пользовательскими параметрами
liteq monitor --host 0.0.0.0 --port 5151 --db tasks.db
```

Затем откройте браузер по адресу: **http://127.0.0.1:5151**

**Возможности:**
- 📊 Статистика в реальном времени (задачи, воркеры, очереди)
- 👷 Мониторинг активных воркеров с метриками производительности
- 📋 Управление задачами (просмотр, отмена)
- 🔄 Автообновление каждые 5 секунд
- 📈 Аналитика по очередям

### Программный мониторинг

```python
from liteq import get_queue_stats, get_failed_tasks, retry_task, get_pending_count

# Получить статистику очередей
stats = get_queue_stats(queue='emails')
print(stats)
# [{'queue': 'emails', 'status': 'pending', 'count': 5, 'avg_attempts': 0}]

# Найти упавшие задачи
failed = get_failed_tasks(limit=10, queue='emails')
for task in failed:
    print(f"Задача {task['id']} упала: {task['last_error']}")
    # Повторить задачу
    retry_task(task['id'])

# Количество ожидающих задач
pending = get_pending_count(queue='emails')
print(f"В очереди emails: {pending} задач")
```

## Длительные задачи

Для задач, которые выполняются долго (обработка больших данных, долгие расчёты и т.д.):

```python
import asyncio
from liteq import task, enqueue, cancel_task

@task
async def process_large_dataset(ctx, dataset_size: int = 1000):
    """Обработка большого датасета с поддержкой паузы и отмены"""
    
    # Загружаем прогресс, если задача возобновилась после паузы
    progress = ctx.load_progress()
    start_from = progress.get("payload", {}).get("processed", 0) if progress else 0
    
    results = []
    for i in range(start_from, dataset_size):
        # Проверяем, не отменили ли задачу
        if ctx.cancelled:
            ctx.save_progress(f"cancelled_at_{i}", {"processed": i})
            return {"status": "cancelled", "processed": i}
        
        # Проверяем, не поставили ли на паузу
        if ctx.paused:
            ctx.save_progress(f"paused_at_{i}", {"processed": i})
            return {"status": "paused", "processed": i}
        
        # Обрабатываем элемент
        await asyncio.sleep(0.1)
        results.append(f"result_{i}")
        
        # Сохраняем чекпоинт каждые 100 элементов
        if (i + 1) % 100 == 0:
            ctx.save_progress(f"step_{i + 1}", {"processed": i + 1})
            print(f"Обработано: {i + 1}/{dataset_size}")
    
    # Сохраняем финальный результат
# Восстановить зависшие задачи (больше 30 минут в обработке)
recover_stuck_tasks(timeout_minutes=30)

# Удалить старые выполненные/упавшие задачи (старше 7 дней)
cleanup_old_tasks(days=7, queue='emails')
```

## Больше примеров

В папке [examples/](../examples/) есть полные рабочие примеры:

- **[basic.py](../examples/basic.py)** — базовое использование с async и sync задачами
- **[multiple_queues.py](../examples/multiple_queues.py)** — работа с несколькими очередями и воркерами
- **[priorities.py](../examples/priorities.py)** — приоритеты задач в действии
- **[long_running.py](../examples/long_running.py)** — длительные задачи с прогрессом, чекпоинтами и отменой
- **[monitoring.py](../examples/monitoring.py)** — мониторинг, статистика и управление задачами
- **[email_campaign.py](../examples/email_campaign.py)** — реальный пример системы email-рассылок

Запустить любой пример:
```bash
python examples/basic.py
```

---

## Зачем LiteQ

* **Просто** — без брокеров и сервисов
* **Легковесно** — только stdlib
* **Быстро** — SQLite тянет больше, чем кажется
* **Надёжно** — данные не пропадают
* **Гибко** — очереди, приоритеты, задержки

---

## Ограничения

- Не подходит для экстремальных нагрузок (миллионы задач в секунду)
- Только одна нода (нет распределённого кластера)
- Есть ограничения SQLite при работе по сети

Если вам нужна высокая пропускная способность или распределённая обработка — присмотритесь к Redis, RabbitMQ или облачным решениям.

## Лицензия

MIT — см. файл [LICENSE](../LICENSE).

## Вклад в проект

Pull request'ы приветствуются! Не стесняйтесь открывать issue или предлагать улучшения.

## Ссылки

- [PyPI](https://pypi.org/project/liteq/)
- [GitHub](https://github.com/ddreamboy/liteq)
- [Документация](https://github.com/ddreamboy/liteq#readme)
