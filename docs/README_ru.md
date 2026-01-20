# LiteQ

<p align="center">
  <a href="https://github.com/ddreamboy/liteq/actions/workflows/tests.yml"><img src="https://github.com/ddreamboy/liteq/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://codecov.io/gh/ddreamboy/liteq"><img src="https://codecov.io/gh/ddreamboy/liteq/branch/master/graph/badge.svg" alt="codecov"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <b>Read in:</b> <a href="../README.md">🇬🇧 English</a>
</p>

Легковесная минималистичная очередь задач для Python **без внешних зависимостей**.

LiteQ — это очередь задач на чистом Python и SQLite. Идеально для фоновой обработки задач без сложности Celery или Redis. Просто добавь декоратор и вызови `.delay()` — вот и всё!

## Возможности

✨ **Ноль зависимостей** — только Python 3.10+ и SQLite  
⚡ **Предельно простой API** — декоратор `@task` и метод `.delay()`  
🔄 **Async и sync** — работает с обычными и асинхронными функциями  
📦 **Несколько очередей** — организуйте задачи по названиям очередей  
🎯 **Приоритеты** — контролируйте порядок выполнения  
🔁 **Автоповторы** — настраиваемая логика повторов  
👷 **Множество воркеров** — параллельная обработка задач  
⏰ **Планировщик** — задачи по расписанию (cron)  
⏱️ **Таймауты** — автоматическое убийство повисших задач  
🚀 **FastAPI** — встроенная поддержка FastAPI  
📊 **Мониторинг** — отслеживание статистики, воркеров и статуса задач  
💾 **Надёжность** — сохранение в SQLite  
🧪 **Production Ready** — покрытие тестами >80%

## Установка

```bash
pip install liteq
```

## Быстрый старт

### 1. Определите задачи

Создайте файл `tasks.py`:

```python
from liteq import task
import time

@task()
def send_email(to: str, subject: str):
    print(f"Отправка письма на {to}: {subject}")
    time.sleep(1)
    return f"Письмо отправлено на {to}"

@task(queue="reports", max_retries=5)
def generate_report(report_id: int):
    print(f"Генерация отчёта {report_id}")
    time.sleep(2)
    return {"report_id": report_id, "status": "готово"}
```

### 2. Добавьте задачи в очередь

```python
from tasks import send_email, generate_report

# Добавляем задачи - они возвращают ID задачи
task_id = send_email.delay(to="user@example.com", subject="Привет!")
print(f"Добавлена задача: {task_id}")

# Добавляем в другую очередь
report_id = generate_report.delay(report_id=123)
```

### 3. Проверьте статус задачи

```python
from liteq import get_task_status

# Получаем статус задачи
status = get_task_status(task_id)
if status:
    print(f"Статус: {status['status']}")  # pending/running/done/failed
    print(f"Попытки: {status['attempts']}/{status['max_retries']}")
    
    if status['status'] == 'done':
        print(f"Результат: {status['result']}")
    elif status['status'] == 'failed':
        print(f"Ошибка: {status['error']}")
```

### 4. Запустите воркер

```bash
# Запускаем воркер для обработки задач
liteq worker --app tasks.py --queues default,reports --concurrency 4
```

Готово! Ваши задачи будут обрабатываться в фоне.

## Примеры

### Интеграция с FastAPI

```python
from fastapi import FastAPI
from liteq import task, get_task_status
from liteq.fastapi import LiteQBackgroundTasks, enqueue_task

app = FastAPI()

@task(queue="emails", timeout=60)
async def send_email(to: str, subject: str):
    # Логика отправки
    return {"sent": True}

# Способ 1: Просто .delay()
@app.post("/send-email")
async def api_send_email(to: str, subject: str):
    task_id = send_email.delay(to, subject)
    return {"task_id": task_id}

# Способ 2: FastAPI-подобный BackgroundTasks с проверкой статуса
@app.post("/send-email-bg")
async def api_send_email_bg(to: str, background: LiteQBackgroundTasks):
    task_id = background.add_task(send_email, to, "Привет!")
    return {"message": "queued", "task_id": task_id}

# Способ 3: Helper-функция
@app.post("/send-email-helper")
async def api_send_email_helper(to: str):
    task_id = enqueue_task(send_email, to, "Добро пожаловать")
    return {"task_id": task_id}

# Проверка статуса задачи
@app.get("/tasks/{task_id}")
async def check_task_status(task_id: int):
    status = get_task_status(task_id)
    if not status:
        return {"error": "Задача не найдена"}, 404
    return {
        "task_id": status["id"],
        "status": status["status"],
        "result": status.get("result"),
        "error": status.get("error")
    }
```

### Запланированные задачи (Cron)

```python
from liteq import task, register_schedule
from liteq.scheduler import Scheduler

@task()
def daily_backup():
    print("Запуск резервного копирования...")
    return {"status": "success"}

@task()
def cleanup():
    print("Очистка...")

# Регистрируем расписание
register_schedule(daily_backup, "0 2 * * *")  # Каждый день в 2 часа ночи
register_schedule(cleanup, "*/5 * * * *")  # Каждые 5 минут

# Запускаем планировщик
scheduler = Scheduler(check_interval=60)
scheduler.run()
```

```bash
# Или через CLI
liteq scheduler --app tasks.py --interval 60
```

### Таймауты задач

```python
from liteq import task

# Таймаут на уровне задачи
@task(timeout=30)  # 30 секунд
def slow_task():
    import time
    time.sleep(100)  # Будет убита через 30с

# Таймаут на уровне воркера
# liteq worker --app tasks.py --timeout 60
```

### Отложенное выполнение

```python
from liteq import task
from datetime import datetime, timedelta

@task()
def reminder(message: str):
    print(f"Напоминание: {message}")

# Запланировать на потом
run_time = datetime.now() + timedelta(hours=1)
task_id = reminder.schedule(run_time, "Встреча через 1 час")
```

### Асинхронные задачи

```python
import asyncio
from liteq import task

@task()
async def fetch_data(url: str):
    print(f"Загрузка {url}")
    await asyncio.sleep(1)
    return {"url": url, "data": "..."}

# Добавление в очередь
task_id = fetch_data.delay(url="https://api.example.com")
```

### Несколько очередей

```python
from liteq import task

@task(queue="emails")
def send_email(to: str):
    print(f"Письмо на {to}")

@task(queue="reports")
def generate_report(id: int):
    print(f"Отчёт {id}")

@task(queue="notifications")
def send_push(user_id: int, message: str):
    print(f"Push для {user_id}: {message}")

# Добавление в разные очереди
send_email.delay(to="user@example.com")
generate_report.delay(id=42)
send_push.delay(user_id=1, message="Привет!")
```

### Настройка задач

```python
from liteq import task

@task(name="custom_email_task", max_retries=5)
def send_email(to: str):
    # Задача будет повторяться до 5 раз при ошибке
    print(f"Отправка на {to}")

@task(max_retries=0)  # Без повторов
def one_time_task():
    print("Выполняется только один раз")
```

### Использование CLI

```bash
# Запуск воркера
liteq worker --app tasks.py

# Несколько очередей
liteq worker --app tasks.py --queues emails,reports,notifications

# Настройка параллелизма
liteq worker --app tasks.py --concurrency 8

# Панель мониторинга (требует liteq[web])
liteq monitor --port 5151
```

### Программный запуск воркера

```python
from liteq.db import init_db
from liteq.worker import Worker

# Инициализация базы данных
init_db()

# Создание и запуск воркера
worker = Worker(queues=["default", "emails"], concurrency=4)
worker.run()  # Блокирующий вызов
```

### Мониторинг

```python
from liteq.monitoring import (
    get_queue_stats,
    get_recent_tasks,
    list_queues,
    get_failed_tasks,
    get_active_workers,
)

# Статистика очередей
stats = get_queue_stats()
for stat in stats:
    print(f"{stat['queue']}: {stat['count']} задач ({stat['status']})")

# Список всех очередей
queues = list_queues()
print(f"Очереди: {queues}")

# Последние задачи
recent = get_recent_tasks(limit=10)

# Упавшие задачи
failed = get_failed_tasks(limit=5)
for task in failed:
    print(f"Задача {task['id']} упала: {task['error']}")

# Активные воркеры
workers = get_active_workers()
for worker in workers:
    print(f"Воркер {worker['worker_id']}: {worker['active_tasks']} активных задач")
```

## Больше примеров

В папке [examples/](../examples/) есть полные рабочие примеры:

- **[basic.py](../examples/basic.py)** — простое введение с async и sync задачами
- **[multiple_queues.py](../examples/multiple_queues.py)** — несколько очередей с разными воркерами
- **[priorities.py](../examples/priorities.py)** — демонстрация приоритетов задач
- **[monitoring.py](../examples/monitoring.py)** — мониторинг и статистика очередей
- **[email_campaign.py](../examples/email_campaign.py)** — реальный пример email-рассылки

Запустить любой пример:
```bash
python examples/basic.py
```

## Справочник API

### Основные функции

#### `get_task_status(task_id: int) -> dict | None`

Получить статус и детали задачи по ID.

**Аргументы:**
- `task_id` (int): ID задачи, возвращённый `.delay()` или `.schedule()`

**Возвращает:** Словарь с информацией о задаче или `None`, если не найдена

**Пример:**
```python
from liteq import task, get_task_status

@task()
def process_data(x: int):
    return x * 2

task_id = process_data.delay(5)

# Проверка статуса
status = get_task_status(task_id)
if status:
    print(f"Статус: {status['status']}")  # pending/running/done/failed
    print(f"Попытки: {status['attempts']}/{status['max_retries']}")
    if status['status'] == 'done':
        print(f"Результат: {status['result']}")
```

### Декоратор

#### `@task(queue='default', max_retries=3, name=None)`

Превращает функцию в задачу.

**Аргументы:**
- `queue` (str): Название очереди (по умолчанию: "default")
- `max_retries` (int): Максимальное число повторов (по умолчанию: 3)
- `name` (str, опционально): Своё имя задачи (по умолчанию: имя функции)

**Возвращает:** Функцию с методом `.delay(*args, **kwargs)`

**Пример:**
```python
@task(queue="emails", max_retries=5)
def send_email(to: str):
    ...

# Добавление в очередь
task_id = send_email.delay(to="user@example.com")
```

### Воркер

#### `Worker(queues, concurrency)`

Создаёт воркер для обработки задач.

**Аргументы:**
- `queues` (list[str]): Список названий очередей для обработки
- `concurrency` (int): Количество параллельных процессов

**Методы:**
- `run()`: Запускает обработку задач (блокирующий вызов)

**Пример:**
```python
from liteq.worker import Worker

worker = Worker(queues=["default", "emails"], concurrency=4)
worker.run()
```

### Функции мониторинга

Все доступны в `liteq.monitoring`:

#### `get_queue_stats() -> list[dict]`

Получить статистику по очередям и статусам.

#### `get_recent_tasks(limit=50) -> list[dict]`

Получить последние задачи по времени создания.

#### `list_queues() -> list[str]`

Получить список всех уникальных названий очередей.

#### `get_failed_tasks(limit=50) -> list[dict]`

Получить последние упавшие задачи.

#### `get_active_workers() -> list[dict]`

Получить активные воркеры (heartbeat < 15 секунд назад).

### База данных

#### `init_db()`

Инициализирует схему базы данных. Автоматически вызывается CLI.

**Пример:**
```python
from liteq.db import init_db

init_db()
```

#### `get_conn()`

Получить соединение с базой данных. Использует переменную окружения `LITEQ_DB` или по умолчанию `liteq.db`.

**Пример:**
```python
from liteq.db import get_conn

with get_conn() as conn:
    tasks = conn.execute("SELECT * FROM tasks WHERE status='pending'").fetchall()
```

## Структура проекта

```
liteq/
├── liteq/
│   ├── __init__.py       # Основные экспорты (@task)
│   ├── core.py           # Декоратор задач и реестр
│   ├── db.py             # Слой базы данных (SQLite)
│   ├── worker.py         # Реализация воркера
│   ├── cli.py            # Интерфейс командной строки
│   ├── monitoring.py     # Статистика и мониторинг
│   └── web.py            # Веб-панель (опционально)
├── examples/             # Полные примеры
├── tests/                # Покрытие >80%
├── README.md
├── pyproject.toml
└── setup.py
```

## Переменные окружения

- `LITEQ_DB` - Путь к файлу базы данных (по умолчанию: `liteq.db`)

```bash
export LITEQ_DB=/path/to/tasks.db
liteq worker --app tasks.py
```

## Схема базы данных

LiteQ использует простую базу данных SQLite с двумя таблицами:

**tasks:**
- `id` - Первичный ключ
- `name` - Имя функции задачи
- `payload` - JSON args/kwargs
- `queue` - Название очереди
- `status` - pending/running/done/failed
- `priority` - Целое число (больше = раньше)
- `attempts` - Текущее количество попыток
- `max_retries` - Максимум повторов
- `worker_id` - ID обрабатывающего воркера
- `run_at` - Время запланированного запуска
- `created_at` - Время создания
- `finished_at` - Время завершения
- `result` - JSON результат
- `error` - Сообщение об ошибке

**workers:**
- `worker_id` - Первичный ключ
- `hostname` - Имя хоста воркера
- `queues` - Очереди через запятую
- `concurrency` - Количество процессов
- `last_heartbeat` - Время последнего пинга

## Применение

- 📧 Очереди отправки email
- 📊 Генерация отчётов  
- 🖼️ Обработка изображений/видео
- 📱 Push-уведомления
- 🧹 Задачи очистки/обслуживания
- 📈 Аналитические пайплайны
- 🔄 Доставка веб-хуков
- 📦 Пакетные операции
- 🔍 Веб-скрапинг
- 💾 Импорт данных

## Зачем LiteQ?

**Просто** - Минимальный API, без конфигурации  
**Легковесно** - Без зависимостей, небольшая кодовая база  
**Быстро** - SQLite удивительно производителен  
**Надёжно** - WAL режим, ACID транзакции  
**Отлаживаемо** - Это просто SQLite, изучайте любым SQL инструментом  
**По-питоновски** - Естественно, не по-энтерпрайзному

## Когда НЕ использовать LiteQ

- Миллионы задач в секунду
- Распределённые/мультинодовые установки
- Сетевые файловые системы (NFS, SMB)
- Задачи размером больше нескольких МБ
- Потоковая обработка в реальном времени

Для этого используйте RabbitMQ, Redis, Kafka или облачные сервисы.

## Лицензия

MIT — см. файл [LICENSE](../LICENSE).

## Вклад в проект

Pull request'ы приветствуются! Не стесняйтесь открывать issue или предлагать улучшения.

## Ссылки

- [PyPI](https://pypi.org/project/liteq/)
- [GitHub](https://github.com/ddreamboy/liteq)
- [Документация](https://github.com/ddreamboy/liteq#readme)
