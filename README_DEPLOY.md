# Деплой Life SSO на VPS

## Требования

- Docker и Docker Compose установлены на VPS
- Минимум 2GB RAM
- 20GB свободного места на диске

## Быстрый старт

### 1. Подготовка на VPS

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd "Life all"

# Убедитесь что .env файл есть в директории бекенда
# Life back2/.env
```

### 2. Настройка .env файла

Создайте или отредактируйте `Life back2/.env`:

```env
# База данных (будет переопределена в docker-compose для подключения к контейнеру)
DATABASE_URL=postgresql://rami:test123455@localhost:5432/lifeback

# JWT настройки
# Сгенерируйте новый SECRET_KEY для продакшена:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_secret_key_min_32_chars_here

# Опционально: отдельный ключ для шифрования биометрии (32 байта = 64 hex символа)
# python -c "import secrets; print(secrets.token_bytes(32).hex())"
ENCRYPTION_KEY=

# Токены срок действия
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

**Важно:** `DATABASE_URL` в `.env` будет автоматически переопределен в docker-compose для подключения к контейнеру PostgreSQL.

### 3. Настройка PostgreSQL в docker-compose.yml

В `docker-compose.yml` настройте PostgreSQL:

```yaml
postgres:
  environment:
    POSTGRES_USER: life_sso_user          # Имя пользователя БД
    POSTGRES_PASSWORD: your_password      # Пароль (лучше через .env)
    POSTGRES_DB: lifeback                 # Имя базы данных
```

**PostgreSQL автоматически создаст:**
- ✅ Пользователя `life_sso_user`
- ✅ Базу данных `lifeback`
- ✅ Установит пароль из `POSTGRES_PASSWORD`

**Ничего создавать вручную не нужно!**

### 4. Создание .env для docker-compose (опционально)

Создайте `.env` в корне проекта для переменных PostgreSQL:

```env
POSTGRES_PASSWORD=your_secure_password_here
```

### 5. Запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Проверка статуса
docker-compose ps
```

### 6. Проверка работы

- Frontend: `http://your-vps-ip:3000`
- Backend API: `http://your-vps-ip:8000`
- API Docs: `http://your-vps-ip:8000/docs`

## Как работает PostgreSQL в Docker

### Автоматическое создание

При первом запуске контейнера PostgreSQL:

1. **Создает пользователя** из `POSTGRES_USER`
2. **Создает базу данных** из `POSTGRES_DB`
3. **Устанавливает пароль** из `POSTGRES_PASSWORD`
4. **Готов к использованию** сразу после запуска

### Подключение из контейнера приложения

В `docker-compose.yml`:
- `DATABASE_URL` использует имя сервиса `postgres` вместо `localhost`
- Это работает благодаря Docker network (`life-sso-network`)

### Подключение с хоста (для отладки)

```bash
# Подключиться к PostgreSQL извне контейнера
psql -h localhost -p 5432 -U life_sso_user -d lifeback

# Или через Docker
docker-compose exec postgres psql -U life_sso_user -d lifeback
```

## Управление

### Остановка
```bash
docker-compose down
```

### Остановка с удалением данных БД
```bash
docker-compose down -v
```

### Перезапуск
```bash
docker-compose restart
```

### Обновление
```bash
# Получить новый код
git pull

# Пересобрать и перезапустить
docker-compose up -d --build
```

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только приложение
docker-compose logs -f app

# Только PostgreSQL
docker-compose logs -f postgres
```

## Настройка Nginx (опционально)

Для продакшена рекомендуется использовать Nginx как reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Безопасность

1. **Обязательно измените пароли** в `Life back2/.env` и `docker-compose.yml`
2. **Используйте HTTPS** (Let's Encrypt через Certbot)
3. **Настройте firewall** (откройте только 80, 443, 22)
4. **Регулярно обновляйте** Docker образы
5. **Делайте бэкапы** базы данных

## Бэкап базы данных

```bash
# Создать бэкап
docker-compose exec postgres pg_dump -U life_sso_user lifeback > backup_$(date +%Y%m%d).sql

# Восстановить из бэкапа
docker-compose exec -T postgres psql -U life_sso_user lifeback < backup_20250101.sql
```

## Мониторинг

```bash
# Использование ресурсов
docker stats

# Использование диска
docker system df
```

## Troubleshooting

### Проблема: Контейнер не запускается
```bash
# Проверьте логи
docker-compose logs app

# Проверьте статус
docker-compose ps
```

### Проблема: База данных недоступна
```bash
# Проверьте подключение
docker-compose exec app python3 -c "from life_backend.database import engine; print(engine.connect())"

# Проверьте логи PostgreSQL
docker-compose logs postgres

# Проверьте что PostgreSQL запущен
docker-compose ps postgres
```

### Проблема: Порты заняты
```bash
# Измените порты в docker-compose.yml
ports:
  - "3001:3000"  # Вместо 3000:3000
  - "8001:8000"  # Вместо 8000:8000
```

## Разделение на отдельные контейнеры (опционально)

Если хотите разделить backend и frontend:

**Плюсы:**
- ✅ Независимое масштабирование
- ✅ Независимые обновления
- ✅ Лучшая изоляция

**Минусы:**
- ❌ Сложнее управление
- ❌ Больше ресурсов
- ❌ Нужна настройка сети

**Рекомендация:** Для начала используйте один контейнер (проще). При необходимости разделите позже.
