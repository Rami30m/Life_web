# Пошаговая инструкция деплоя на VPS

## ✅ Правильный порядок действий:

1. **Отправить проект на сервер** (через Git, SCP, или другой способ)
2. **На сервере создать .env файл**
3. **На сервере собрать и запустить docker-compose**

---

## 📤 Шаг 1: Отправка проекта на сервер

### Вариант A: Через Git (рекомендуется)

```bash
# На вашем компьютере
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-git-repo-url>
git push -u origin main

# На сервере
git clone <your-git-repo-url>
cd "Life all"
```

### Вариант B: Через SCP (если нет Git)

```bash
# На вашем компьютере (Windows PowerShell)
scp -r "C:\Users\RAMIH\Desktop\Life all" user@your-vps-ip:/home/user/

# Или через WinSCP (GUI)
```

### Вариант C: Через rsync (если установлен)

```bash
# На вашем компьютере
rsync -avz "C:\Users\RAMIH\Desktop\Life all" user@your-vps-ip:/home/user/
```

---

## 🔧 Шаг 2: Подготовка на сервере

### 2.1. Установка Docker и Docker Compose (если не установлены)

```bash
# Подключитесь к серверу
ssh user@your-vps-ip

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка
docker --version
docker-compose --version
```

### 2.2. Переход в директорию проекта

```bash
cd "Life all"
# или
cd "/home/user/Life all"
```

### 2.3. Создание .env файла в корне проекта

```bash
# Создайте .env файл
nano .env
```

**Содержимое `.env`:**

```env
# Пароль для PostgreSQL (используется в docker-compose)
POSTGRES_PASSWORD=your_secure_password_here_change_me
```

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 2.4. Проверка .env файла бекенда

Убедитесь что `Life back2/.env` существует и содержит:

```env
# База данных (будет переопределена docker-compose)
DATABASE_URL=postgresql://rami:test123455@localhost:5432/lifeback

# JWT настройки
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
ENCRYPTION_KEY=
```

---

## 🚀 Шаг 3: Сборка и запуск на сервере

### 3.1. Сборка и запуск (первый раз)

```bash
# Сборка образов и запуск контейнеров
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f
```

**Что происходит:**
- ✅ Собирается образ приложения (frontend + backend)
- ✅ Скачивается образ PostgreSQL
- ✅ Создается пользователь и база данных PostgreSQL
- ✅ Запускаются оба контейнера
- ✅ Приложение подключается к БД

### 3.2. Проверка статуса

```bash
# Проверка запущенных контейнеров
docker-compose ps

# Должно показать:
# NAME                  STATUS
# life-sso-app          Up
# life-sso-postgres     Up
```

### 3.3. Проверка работы

```bash
# Проверка логов приложения
docker-compose logs app

# Проверка логов PostgreSQL
docker-compose logs postgres

# Проверка подключения к БД из контейнера
docker-compose exec app python3 -c "from life_backend.database import engine; print(engine.connect())"
```

---

## 🔄 Обновление проекта (после изменений)

```bash
# На сервере
cd "Life all"

# Получить новые изменения (если через Git)
git pull

# Пересобрать и перезапустить
docker-compose up -d --build

# Или только перезапустить (если код не менялся)
docker-compose restart
```

---

## 🛑 Остановка и удаление

```bash
# Остановить контейнеры
docker-compose down

# Остановить и удалить данные БД (ОСТОРОЖНО!)
docker-compose down -v
```

---

## 📋 Чек-лист перед деплоем

- [ ] Проект отправлен на сервер
- [ ] Docker и Docker Compose установлены
- [ ] Создан `.env` в корне проекта с `POSTGRES_PASSWORD`
- [ ] Проверен `Life back2/.env` с правильными переменными
- [ ] Порты 3000 и 8000 свободны на сервере
- [ ] Firewall настроен (если нужен доступ извне)

---

## 🔍 Troubleshooting

### Проблема: "Cannot connect to Docker daemon"

```bash
# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER
# Выйдите и войдите снова
```

### Проблема: "Port already allocated"

```bash
# Проверьте что использует порт
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :8000

# Или измените порты в docker-compose.yml
```

### Проблема: "Permission denied"

```bash
# Дайте права на выполнение
chmod +x start.sh
```

---

## 📝 Важные замечания

1. **Не коммитьте .env файлы в Git!** Они должны быть в `.gitignore`
2. **Используйте сильные пароли** для `POSTGRES_PASSWORD` и `SECRET_KEY`
3. **Настройте firewall** на сервере (откройте только нужные порты)
4. **Используйте HTTPS** в продакшене (через Nginx + Let's Encrypt)

