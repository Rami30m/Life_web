# 🏗️ Архитектура SSO для Life SSO

## 📋 Анализ требований

### Текущее состояние
- ✅ Базовая аутентификация (email/password, биометрия)
- ✅ JWT токены (Access + Refresh)
- ✅ Пользователи в БД
- ✅ Безопасное хранение данных

### Новые требования
Нужны **3 способа входа на внешние платформы** компании:

1. **Простая переадресация** — OAuth 2.0 Authorization Code Flow
2. **QR-код** — OAuth Device Flow (адаптированный)
3. **Вход по кодам** — Magic Link / One-Time Password

---

## 🎯 Концепция SSO

### Что такое SSO (Single Sign-On)?
**Life SSO** — централизованная система аутентификации, позволяющая пользователям войти один раз и получить доступ ко всем платформам компании без повторного ввода пароля.

### Преимущества для компании:
- ✅ Единый источник правды (единая БД пользователей)
- ✅ Упрощенное управление доступом
- ✅ Лучший UX (не нужно помнить N паролей)
- ✅ Централизованная безопасность

---

## 🔄 Метод 1: Простая переадресация (OAuth 2.0)

### Схема работы:

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Платформа │         │  Life SSO    │         │   Пользователь │
│  (Клиент)   │         │  (Сервер)    │         │              │
└──────┬──────┘         └──────┬───────┘         └──────┬───────┘
       │                       │                       │
       │  1. Редирект на       │                       │
       │     /sso/authorize    │                       │
       ├──────────────────────>│                       │
       │     ?client_id=...    │                       │
       │     &redirect_uri=... │                       │
       │                       │                       │
       │                       │  2. Показывает форму │
       │                       │     входа            │
       │                       ├──────────────────────>│
       │                       │                       │
       │                       │  3. Пользователь     │
       │                       │     вводит данные    │
       │                       │<──────────────────────┤
       │                       │                       │
       │                       │  4. Проверяет        │
       │                       │     credentials      │
       │                       │                       │
       │                       │  5. Генерирует       │
       │                       │     authorization    │
       │                       │     code              │
       │                       │                       │
       │  6. Редирект обратно │                       │
       │     с code            │                       │
       │<──────────────────────┤                       │
       │     ?code=abc123      │                       │
       │                       │                       │
       │  7. Обменивает code   │                       │
       │     на токены         │                       │
       │├──────────────────────>│                       │
       │     POST /sso/token   │                       │
       │     code + client_secret│                     │
       │                       │                       │
       │  8. Возвращает        │                       │
       │     access_token,     │                       │
       │     refresh_token,    │                       │
       │     user_data         │                       │
       │<──────────────────────┤                       │
       │                       │                       │
       │  9. Вход выполнен!    │                       │
       │     Пользователь      │                       │
       │     аутентифицирован  │                       │
       │                       │                       │
```

### Поток данных:

**Шаг 1: Платформа перенаправляет на Life SSO**
```
https://life-sso.com/sso/authorize?
  client_id=platform_123
  &redirect_uri=https://platform.com/callback
  &response_type=code
  &state=random_string_for_security
  &scope=openid profile email
```

**Шаг 2: Пользователь логинится в Life SSO**
- Показывается форма входа
- Поддерживается: пароль, биометрия, QR (если есть сессия)

**Шаг 3: Life SSO возвращает authorization code**
```
https://platform.com/callback?
  code=abc123xyz
  &state=random_string_for_security
```

**Шаг 4: Платформа обменивает code на токены**
```http
POST /sso/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=abc123xyz
&client_id=platform_123
&client_secret=secret_456
&redirect_uri=https://platform.com/callback
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "xyz789abc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Иван Иванов",
    "phone": "+79001234567"
  }
}
```

### Безопасность:
- ✅ `client_secret` хранится только на сервере платформы
- ✅ `state` параметр защищает от CSRF
- ✅ Authorization code одноразовый (используется один раз)
- ✅ Code истекает через 10 минут

---

## 📱 Метод 2: Вход по QR-коду

### Схема работы:

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Платформа │         │  Life SSO    │         │ Мобильное   │
│  (Клиент)   │         │  (Сервер)    │         │ приложение  │
└──────┬──────┘         └──────┬───────┘         └──────┬───────┘
       │                       │                       │
       │  1. Запрашивает      │                       │
       │     device_code      │                       │
       ├──────────────────────>│                       │
       │                       │                       │
       │  2. Возвращает        │                       │
       │     device_code,     │                       │
       │     user_code,       │                       │
       │     verification_uri │                       │
       │<──────────────────────┤                       │
       │                       │                       │
       │  3. Показывает QR     │                       │
       │     с user_code      │                       │
       │     и URL            │                       │
       │                       │                       │
       │                       │  4. Сканирует QR     │
       │                       │     и открывает      │
       │                       │<──────────────────────┤
       │                       │     Life SSO в браузере│
       │                       │                       │
       │                       │  5. Вводит user_code │
       │                       │     и логинится       │
       │                       │                       │
       │  6. Polling: Проверяет│                       │
       │     статус device_code│                       │
       │├──────────────────────>│                       │
       │     каждые 5 сек      │                       │
       │                       │                       │
       │  7. Возвращает        │                       │
       │     "pending" или    │                       │
       │     "authorized"      │                       │
       │<──────────────────────┤                       │
       │                       │                       │
       │  8. Когда authorized: │                       │
       │     Обменивает        │                       │
       │     device_code       │                       │
       │     на токены         │                       │
       │├──────────────────────>│                       │
       │                       │                       │
       │  9. Получает токены   │                       │
       │     и данные           │                       │
       │<──────────────────────┤                       │
       │                       │                       │
       │  10. Вход выполнен!   │                       │
       │                       │                       │
```

### Поток данных:

**Шаг 1: Платформа запрашивает QR сессию**
```http
POST /sso/qr/initiate
Content-Type: application/json

{
  "client_id": "platform_123",
  "scope": "openid profile email"
}
```

**Ответ (ВАРИАНТ A — платформа генерирует QR):**
```json
{
  "device_code": "device_abc123",
  "user_code": "ABCD-1234",
  "verification_uri": "https://life-sso.com/sso/qr/verify",
  "verification_uri_complete": "https://life-sso.com/sso/qr/verify?user_code=ABCD-1234",
  "expires_in": 600,
  "interval": 5
}
```
*(Платформа генерирует QR-код из `verification_uri_complete`)*

**Ответ (ВАРИАНТ B — Life SSO возвращает готовый QR):**
```json
{
  "device_code": "device_abc123",
  "user_code": "ABCD-1234",
  "verification_uri": "https://life-sso.com/sso/qr/verify",
  "verification_uri_complete": "https://life-sso.com/sso/qr/verify?user_code=ABCD-1234",
  "qr_code_image": "data:image/png;base64,iVBORw0KGgoAAAANS...",  // Base64 изображение QR
  "qr_code_url": "https://life-sso.com/sso/qr/image/device_abc123",  // Или URL к изображению
  "expires_in": 600,
  "interval": 5
}
```
*(Платформа просто показывает готовое изображение QR)*

**Шаг 2: Отображение QR-кода**

**ВАРИАНТ A: Платформа генерирует QR** (текущая архитектура)
- Платформа получает `verification_uri_complete`
- Платформа генерирует QR-код изображение на своей стороне
- Показывает QR на своей странице
- Пользователь сканирует QR на телефоне

**ВАРИАНТ B: Life SSO возвращает готовый QR** (альтернатива)
- Life SSO генерирует QR-код изображение (Base64 или URL)
- Платформа просто отображает полученное изображение
- ✅ Преимущество: Платформе не нужна библиотека для генерации QR

**Рекомендация:** ВАРИАНТ A (платформа генерирует) — более гибкий, платформа контролирует дизайн QR

**Шаг 3: Пользователь логинится через QR**
- Открывается страница Life SSO с `user_code`
- Пользователь вводит пароль или использует биометрию
- Life SSO связывает `device_code` с пользователем

**Шаг 4: Платформа проверяет статус (polling)**
```http
POST /sso/qr/token
Content-Type: application/json

{
  "device_code": "device_abc123",
  "client_id": "platform_123",
  "client_secret": "secret_456"
}
```

**Пока pending:**
```json
{
  "status": "pending",
  "message": "Ожидание авторизации..."
}
```

**Когда авторизовано:**
```json
{
  "status": "authorized",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "xyz789abc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Иван Иванов"
  }
}
```

### Безопасность:
- ✅ `device_code` одноразовый
- ✅ `user_code` короткий и удобный для ввода
- ✅ QR-код истекает через 10 минут
- ✅ Polling ограничен (не чаще каждые 5 секунд)

---

## 🔢 Метод 3: Вход по кодам (Magic Link / OTP)

### Схема работы:

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Платформа │         │  Life SSO    │         │   Пользователь │
│  (Клиент)   │         │  (Сервер)    │         │              │
└──────┬──────┘         └──────┬───────┘         └──────┬───────┘
       │                       │                       │
       │  1. Пользователь      │                       │
       │     вводит email      │                       │
       │     или имя           │                       │
       │                       │                       │
       │  2. Запрос на         │                       │
       │     отправку кода     │                       │
       ├──────────────────────>│                       │
       │     POST /sso/code/request│                  │
       │     {email: "user@..."}│                      │
       │                       │                       │
       │  3. Генерирует 6-цифр │                       │
       │     код, сохраняет в  │                       │
       │     БД, отправляет    │                       │
       │     на Life SSO       │                       │
       │                       │                       │
       │  4. Показывает        │                       │
       │     страницу ввода    │                       │
       │     кода на Life SSO  │                       │
       │<──────────────────────┤──────────────────────>│
       │                       │                       │
       │                       │  5. Пользователь     │
       │                       │     вводит код       │
       │                       │<──────────────────────┤
       │                       │                       │
       │                       │  6. Проверяет код    │
       │                       │                       │
       │  7. Платформа         │                       │
       │     проверяет код     │                       │
       ├──────────────────────>│                       │
       │     POST /sso/code/verify│                    │
       │     {code: "123456"}  │                       │
       │                       │                       │
       │  8. Возвращает токены│                       │
       │     если код верный   │                       │
       │<──────────────────────┤                       │
       │                       │                       │
       │  9. Вход выполнен!    │                       │
       │                       │                       │
```

### Поток данных:

**Шаг 1: Пользователь вводит email/имя на платформе**
- Форма: "Введите email или имя для получения кода"

**Шаг 2: Платформа запрашивает код**
```http
POST /sso/code/request
Content-Type: application/json

{
  "client_id": "platform_123",
  "identifier": "user@example.com",  // email или имя
  "redirect_uri": "https://platform.com/callback"
}
```

**Ответ (ВАРИАНТ A — код на Life SSO):**
```json
{
  "code_id": "code_xyz789",
  "message": "Код отправлен. Проверьте ваш Life SSO",
  "expires_in": 300
}
```

**Ответ (ВАРИАНТ B — код возвращается платформе):**
```json
{
  "code_id": "code_xyz789",
  "code": "123456",
  "message": "Введите код на платформе",
  "expires_in": 300
}
```
*(Код показывается на платформе, пользователь вводит его там же)*

**Ответ (ВАРИАНТ C — код по email/SMS):**
```json
{
  "code_id": "code_xyz789",
  "message": "Код отправлен на ваш email/SMS",
  "expires_in": 300
}
```

**Шаг 3: Генерация и отображение кода**

**ВАРИАНТ A: Код показывается на Life SSO** (текущая архитектура)
- Life SSO генерирует 6-цифровой код (например: `123456`)
- Сохраняет в БД с привязкой к `code_id`, пользователю
- Показывает код на странице Life SSO (уведомление/баннер)
- Пользователь должен открыть Life SSO в другой вкладке
- Затем вводит код на платформе

**ВАРИАНТ B: Код показывается на платформе** (проще для пользователя)
- Life SSO генерирует код и возвращает его в ответе на `/sso/code/request`
- Платформа показывает код пользователю сразу
- Пользователь видит код прямо на странице платформы
- ✅ Преимущество: Не нужно переключаться между вкладками

**ВАРИАНТ C: Код отправляется по email/SMS**
- Life SSO генерирует код
- Отправляет код на email/SMS пользователя
- Пользователь получает код и вводит на платформе
- ✅ Преимущество: Не нужно открывать Life SSO

**Рекомендация:** ВАРИАНТ B (код на платформе) — самый простой UX

**Шаг 6: Платформа проверяет код**
```http
POST /sso/code/verify
Content-Type: application/json

{
  "client_id": "platform_123",
  "client_secret": "secret_456",
  "code_id": "code_xyz789",
  "code": "123456"
}
```

**Если код верный:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "xyz789abc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Иван Иванов"
  }
}
```

**Если код неверный:**
```json
{
  "error": "invalid_code",
  "message": "Неверный код. Попробуйте еще раз."
}
```

### Альтернативный вариант: Magic Link
Вместо кода можно отправить **одноразовую ссылку**:
```
https://life-sso.com/sso/code/verify?code_id=xyz789&magic_token=abc123
```
- Пользователь кликает на ссылку
- Life SSO автоматически авторизует и редиректит на платформу

### Безопасность:
- ✅ Код истекает через 5 минут
- ✅ Код одноразовый (после использования удаляется)
- ✅ Ограничение попыток (max 5 попыток)
- ✅ Rate limiting (1 запрос кода в минуту на email)

---

## 🗄️ Модели данных для БД

### 1. Таблица `oauth_clients` (Платформы)

```sql
CREATE TABLE oauth_clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(100) UNIQUE NOT NULL,
    client_secret VARCHAR(255) NOT NULL,  -- Хешированный
    name VARCHAR(200) NOT NULL,  -- Название платформы
    redirect_uri TEXT NOT NULL,  -- Куда возвращать после авторизации
    allowed_scopes TEXT,  -- Какие данные можно запросить
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Таблица `oauth_authorization_codes` (OAuth Code Flow)

```sql
CREATE TABLE oauth_authorization_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);
```

### 3. Таблица `oauth_device_codes` (QR Flow)

```sql
CREATE TABLE oauth_device_codes (
    id SERIAL PRIMARY KEY,
    device_code VARCHAR(100) UNIQUE NOT NULL,
    user_code VARCHAR(20) UNIQUE NOT NULL,
    client_id VARCHAR(100) NOT NULL,
    user_id INTEGER,  -- NULL пока не авторизован
    scope TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, authorized, expired
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);
```

### 4. Таблица `oauth_verification_codes` (Code Flow)

```sql
CREATE TABLE oauth_verification_codes (
    id SERIAL PRIMARY KEY,
    code_id VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(10) NOT NULL,  -- 6-цифровой код
    client_id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL,
    redirect_uri TEXT,
    attempts INTEGER DEFAULT 0,  -- Количество попыток ввода
    max_attempts INTEGER DEFAULT 5,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id)
);
```

---

## 🔌 API Эндпоинты

### OAuth 2.0 Authorization Code Flow

#### 1. `GET /sso/authorize`
Инициация OAuth flow
- **Параметры:** `client_id`, `redirect_uri`, `response_type=code`, `state`, `scope`
- **Действие:** Показывает форму входа
- **Возврат:** Редирект на `redirect_uri` с `code` и `state`

#### 2. `POST /sso/token`
Обмен authorization code на токены
- **Body:** `grant_type=authorization_code`, `code`, `client_id`, `client_secret`, `redirect_uri`
- **Возврат:** `access_token`, `refresh_token`, `user`

### QR Code Flow

#### 3. `POST /sso/qr/initiate`
Создание QR сессии
- **Body:** `client_id`, `scope`
- **Возврат:** `device_code`, `user_code`, `verification_uri`, `expires_in`

#### 4. `GET /sso/qr/verify?user_code=ABCD-1234`
Страница для входа по QR
- **Действие:** Показывает форму входа с `user_code`
- **После входа:** Обновляет статус `device_code` на `authorized`

#### 5. `POST /sso/qr/token`
Проверка статуса и получение токенов
- **Body:** `device_code`, `client_id`, `client_secret`
- **Возврат:** `status` (pending/authorized) или токены

### Code Flow (Magic Link / OTP)

#### 6. `POST /sso/code/request`
Запрос кода для входа
- **Body:** `client_id`, `identifier` (email или имя)
- **Возврат:** `code_id`, `expires_in`

#### 7. `GET /sso/code/verify?code_id=xyz789&token=abc123` (Magic Link)
Автоматическая верификация по ссылке
- **Действие:** Проверяет token и авторизует пользователя
- **Возврат:** Редирект на платформу с токенами

#### 8. `POST /sso/code/verify`
Верификация введенного кода
- **Body:** `client_id`, `client_secret`, `code_id`, `code`
- **Возврат:** Токены или ошибка

### Управление клиентами

#### 9. `POST /sso/clients` (Admin only)
Создание новой платформы
- **Body:** `name`, `redirect_uri`, `allowed_scopes`
- **Возврат:** `client_id`, `client_secret`

#### 10. `GET /sso/clients` (Admin only)
Список всех платформ

---

## 🔒 Безопасность

### Защита секретов
- ✅ `client_secret` хранится в БД в хешированном виде (bcrypt)
- ✅ `client_secret` передается только по HTTPS
- ✅ `client_secret` никогда не отправляется на фронтенд

### Защита от атак
- ✅ **CSRF:** Параметр `state` в OAuth flow
- ✅ **Replay Attack:** Коды одноразовые и с TTL
- ✅ **Brute Force:** Rate limiting на все эндпоинты
- ✅ **SQL Injection:** SQLAlchemy ORM (параметризованные запросы)

### Валидация
- ✅ Проверка `redirect_uri` (должен быть зарегистрирован)
- ✅ Проверка `scope` (только разрешенные scope)
- ✅ Проверка истечения кодов/токенов

---

## 📊 Сравнение методов

| Метод | Удобство | Безопасность | Сложность реализации | Когда использовать |
|-------|----------|--------------|---------------------|-------------------|
| **Переадресация** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Средняя | Веб-приложения |
| **QR-код** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Высокая | Публичные экраны, TV |
| **Коды** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Низкая | Когда нет доступа к Life SSO |

---

## 🚀 Этапы разработки

### **ЭТАП 1: Базовая инфраструктура SSO**
1. Создать модели БД (`oauth_clients`, `oauth_authorization_codes`, и т.д.)
2. Создать миграции Alembic
3. Создать схемы Pydantic для SSO
4. Реализовать админ-панель для управления клиентами (`/sso/clients`)

### **ЭТАП 2: OAuth 2.0 Authorization Code Flow**
1. Реализовать `GET /sso/authorize`
2. Реализовать `POST /sso/token`
3. Добавить страницу входа с `state` параметром
4. Тестирование с mock платформой

### **ЭТАП 3: QR Code Flow**
1. Реализовать `POST /sso/qr/initiate`
2. Реализовать `GET /sso/qr/verify`
3. Реализовать `POST /sso/qr/token` (polling)
4. Добавить QR-генератор на фронтенде
5. Тестирование полного потока

### **ЭТАП 4: Code Flow (Magic Link / OTP)**
1. Реализовать `POST /sso/code/request`
2. Реализовать генерацию 6-цифрового кода
3. Реализовать `POST /sso/code/verify`
4. Добавить страницу отображения кода на Life SSO
5. Опционально: Magic Link (`GET /sso/code/verify?token=...`)
6. Тестирование

### **ЭТАП 5: Безопасность и оптимизация**
1. Хеширование `client_secret` в БД
2. Rate limiting на все SSO эндпоинты
3. Валидация `redirect_uri`
4. Логирование всех SSO операций
5. Тестирование безопасности

### **ЭТАП 6: Документация и примеры**
1. Создать документацию API для разработчиков платформ
2. Создать примеры интеграции (SDK для популярных языков)
3. Создать тестовую платформу для демонстрации

---

## 🎯 Вопросы для уточнения

1. **QR-код: кто генерирует?**
   - ❓ **Платформа** генерирует QR из URL (вариант A) — нужно ли платформе библиотека QR?
   - ❓ **Life SSO** возвращает готовое изображение QR (вариант B) — проще для платформы

2. **Обычный код (6-цифровой): где показывается?**
   - ❓ **Life SSO** генерирует и показывает на своей странице (вариант A)
   - ❓ **Life SSO** генерирует, возвращает платформе, платформа показывает (вариант B) ⭐ Рекомендуется
   - ❓ **Life SSO** генерирует и отправляет по email/SMS (вариант C)

3. **Нужна ли админ-панель для управления платформами?**
   - Кто будет регистрировать новые платформы?
   - Нужны ли статистика и логи?

4. **Нужна ли поддержка refresh токенов для платформ?**
   - Или только access токены?

5. **Какие данные пользователя нужны платформам?**
   - Минимальный набор: `id`, `email`, `full_name`?
   - Или больше полей?

6. **Нужна ли поддержка logout из всех платформ?**
   - Если пользователь выходит из Life SSO, нужно ли его разлогинивать везде?

---

**Документ создан:** 2025  
**Версия:** 1.0  
**Статус:** Готов к обсуждению и доработке

