# FastAPI + PostgreSQL проект

## Установка

1. Установите зависимости:
```bash
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary python-dotenv
```

2. Настройте подключение к PostgreSQL в файле `database.py`:
```python
DATABASE_URL = "postgresql://пользователь:пароль@хост:порт/имя_бд"
```

Пример:
```python
DATABASE_URL = "postgresql://postgres:admin@localhost:5432/myapp"
```

## Запуск

Запустите сервер:
```bash
uvicorn main:app --reload
```

Приложение будет доступно по адресу: http://127.0.0.1:8000

## API документация

После запуска откройте в браузере:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Структура проекта

- `main.py` - основной файл приложения с эндпоинтами
- `database.py` - настройка подключения к PostgreSQL
- `models.py` - модели SQLAlchemy (таблицы БД)
- `schemas.py` - Pydantic схемы для валидации данных

## Доступные эндпоинты

### Items (Элементы)
- `POST /items/` - создать элемент
- `GET /items/` - получить список элементов
- `GET /items/{item_id}` - получить элемент по ID
- `PUT /items/{item_id}` - обновить элемент
- `DELETE /items/{item_id}` - удалить элемент

### Users (Пользователи)
- `POST /users/` - создать пользователя
- `GET /users/` - получить список пользователей
- `GET /users/{user_id}` - получить пользователя по ID

## Пример использования

### Создание элемента
```bash
curl -X POST "http://127.0.0.1:8000/items/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Laptop",
    "description": "Gaming laptop",
    "price": 1500
  }'
```

### Получение всех элементов
```bash
curl "http://127.0.0.1:8000/items/"
```

## Настройка PostgreSQL

1. Установите PostgreSQL
2. Создайте базу данных:
```sql
CREATE DATABASE myapp;
```

3. Создайте пользователя (опционально):
```sql
CREATE USER myuser WITH PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE myapp TO myuser;
```

4. Обновите `DATABASE_URL` в `database.py` с вашими данными

## Миграции

Таблицы создаются автоматически при запуске приложения благодаря:
```python
models.Base.metadata.create_all(bind=engine)
```

Для production рекомендуется использовать Alembic для миграций.


