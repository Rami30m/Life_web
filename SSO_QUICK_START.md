# ⚡ Life SSO - Быстрый старт

## Шаг 1: Регистрация платформы

Отправьте POST запрос на `/sso/clients` (требуется авторизация):

```bash
curl -X POST http://localhost:8000/sso/clients \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Platform",
    "redirect_uri": "http://localhost:3001/callback",
    "allowed_scopes": "openid profile email"
  }'
```

**Сохраните `client_id` и `client_secret`!**

## Шаг 2: Выбор метода входа

### Вариант A: Authorization Code Flow (Рекомендуется)

**1. Редирект пользователя:**

```
GET http://localhost:8000/sso/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&state=RANDOM_STRING
```

**2. Обработка callback:**

Пользователь вернется на `redirect_uri` с параметром `code`.

**3. Обмен code на токены:**

```bash
curl -X POST http://localhost:8000/sso/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "code": "AUTHORIZATION_CODE",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "YOUR_REDIRECT_URI"
  }'
```

### Вариант B: QR Code Flow

**1. Создание QR сессии:**

```bash
curl -X POST http://localhost:8000/sso/qr/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "scope": "openid profile email"
  }'
```

**2. Polling статуса:**

```bash
curl -X POST http://localhost:8000/sso/qr/token \
  -H "Content-Type: application/json" \
  -d '{
    "device_code": "DEVICE_CODE",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }'
```

Повторяйте polling каждые 5 секунд пока статус не станет `authorized`.

### Вариант C: Code Flow

**1. Запрос кода:**

```bash
curl -X POST http://localhost:8000/sso/code/request \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "identifier": "user@example.com"
  }'
```

**2. Пользователь видит код в Life SSO**

**3. Проверка кода:**

```bash
curl -X POST http://localhost:8000/sso/code/verify \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "code_id": "CODE_ID",
    "code": "123456"
  }'
```

## Шаг 3: Использование токенов

Все методы возвращают JWT токены:

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { ... }
}
```

Используйте `access_token` в заголовке:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Примеры

Смотрите:
- **Полная документация:** `SSO_API_DOCUMENTATION.md`
- **Примеры кода:** `SSO_INTEGRATION_EXAMPLES.md`

## Важные замечания

1. ⚠️ **НИКОГДА** не храните `client_secret` в клиентском коде
2. ✅ Всегда используйте HTTPS в продакшене
3. ✅ Проверяйте `state` параметр для защиты от CSRF
4. ✅ Используйте rate limiting на своей стороне

---

**Нужна помощь?** Смотрите полную документацию в `SSO_API_DOCUMENTATION.md`


