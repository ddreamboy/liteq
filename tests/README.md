# LiteQ Tests

Тесты для библиотеки LiteQ.

## Структура тестов

- **test_basic.py** - Базовые тесты декоратора @task и постановки задач в очередь
- **test_database.py** - Тесты работы с базой данных SQLite
- **test_worker.py** - Тесты worker'ов и их функционала
- **test_integration.py** - Интеграционные тесты выполнения задач

## Запуск тестов

### Все тесты
```bash
pytest
```

### Конкретный файл
```bash
pytest tests/test_basic.py
```

### С подробным выводом
```bash
pytest -v
```

### С покрытием кода
```bash
pytest --cov=liteq --cov-report=html
```

## Требования

```bash
pip install pytest pytest-asyncio
```

## Тестовая база данных

Каждый тест использует отдельную тестовую базу данных, которая автоматически удаляется после выполнения теста.
