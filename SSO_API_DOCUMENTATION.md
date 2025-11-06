# 📚 Life SSO API - Полная документация

## Оглавление

1. [Введение](#введение)
2. [Быстрый старт](#быстрый-старт)
3. [Аутентификация](#аутентификация)
4. [OAuth 2.0 Authorization Code Flow](#oauth-20-authorization-code-flow)
5. [QR Code Flow](#qr-code-flow)
6. [Code Flow (Magic Link / OTP)](#code-flow-magic-link--otp)
7. [Управление клиентами](#управление-клиентами)
8. [Схемы данных](#схемы-данных)
9. [Коды ошибок](#коды-ошибок)
10. [Безопасность](#безопасность)
11. [Примеры интеграции](#примеры-интеграции)
12. [FAQ](#faq)

---

## Введение

**Life SSO** — это централизованная система единого входа (Single Sign-On), позволяющая пользователям авторизоваться один раз и получать доступ ко всем платформам компании.

### Основные возможности

- ✅ **OAuth 2.0 Authorization Code Flow** — стандартный OAuth flow для веб-приложений
- ✅ **QR Code Flow** — вход через сканирование QR-кода (для публичных экранов, TV)
- ✅ **Code Flow** — вход через 6-цифровой код (Magic Link / OTP)
- ✅ **Безопасность** — rate limiting, валидация, логирование
- ✅ **JWT токены** — access и refresh токены с автоматическим обновлением

### Базовый URL

```
http://localhost:8000  # Development
https://sso.life.com    # Production (пример)
```

---

## Быстрый старт

### 1. Регистрация платформы

Сначала нужно зарегистрировать вашу платформу в Life SSO и получить `client_id` и `client_secret`.

**Endpoint:** `POST /sso/clients`

**Запрос:**
```json
{
  "name": "My Platform",
  "redirect_uri": "https://myplatform.com/callback",
  "allowed_scopes": "openid profile email"
}
```

**Ответ:**
```json
{
  "client_id": "abc123...",
  "client_secret": "xyz789...",
  "name": "My Platform",
  "redirect_uri": "https://myplatform.com/callback",
  "allowed_scopes": "openid profile email",
  "message": "Клиент успешно создан. Сохраните client_secret, он больше не будет показан!"
}
```

⚠️ **ВАЖНО:** Сохраните `client_secret` сразу, он больше не будет показан!

### 2. Выбор метода входа

Выберите подходящий метод входа для вашей платформы:

- **Authorization Code Flow** — для веб-приложений
- **QR Code Flow** — для публичных экранов / TV
- **Code Flow** — для случаев, когда пользователь не может открыть Life SSO

---

## Аутентификация

### Получение токенов

После успешной авторизации пользователя, Life SSO возвращает JWT токены:

- **Access Token** — используется для авторизации запросов к API платформы (срок жизни: 15 минут)
- **Refresh Token** — используется для обновления access token (срок жизни: 30 дней)

### Структура ответа с токенами

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Иван Иванов",
    "phone": "+79001234567",
    "birth_date": "1990-01-01",
    "is_active": true,
    "is_biometric_verified": false
  }
}
```

### Использование Access Token

Добавьте токен в заголовок `Authorization`:

```
Authorization: Bearer <access_token>
```

---

## OAuth 2.0 Authorization Code Flow

Стандартный OAuth 2.0 flow для веб-приложений. Подходит для большинства случаев.

### Шаг 1: Редирект на Life SSO

Перенаправьте пользователя на Life SSO с параметрами:

```
GET /sso/authorize?client_id={client_id}&redirect_uri={redirect_uri}&state={state}&scope={scope}
```

**Параметры:**

| Параметр | Обязательный | Описание |
|----------|--------------|----------|
| `client_id` | ✅ | ID вашей платформы |
| `redirect_uri` | ✅ | URI для возврата после авторизации (должен совпадать с зарегистрированным) |
| `response_type` | ❌ | Всегда `code` (по умолчанию) |
| `state` | ❌ | CSRF защита — случайная строка для проверки |
| `scope` | ❌ | Запрашиваемые разрешения (по умолчанию: `openid profile email`) |

**Пример:**

```javascript
const state = generateRandomString();
const params = new URLSearchParams({
  client_id: 'your_client_id',
  redirect_uri: 'https://myplatform.com/callback',
  state: state,
  scope: 'openid profile email'
});

window.location.href = `http://localhost:8000/sso/authorize?${params}`;
```

### Шаг 2: Пользователь входит на Life SSO

Пользователь видит форму входа и может войти одним из способов:
- **Email/Пароль** — стандартный способ входа
- **Биометрия** — вход через распознавание лица (если зарегистрирована)

### Шаг 3: Получение authorization code

После успешного входа, пользователь редиректится обратно на `redirect_uri` с параметрами:

```
https://myplatform.com/callback?code={authorization_code}&state={state}
```

**Параметры:**

| Параметр | Описание |
|----------|----------|
| `code` | Authorization code (одноразовый, живет 10 минут) |
| `state` | Тот же state, что был отправлен (проверьте на CSRF) |

**Пример обработки:**

```javascript
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');

// Проверяем state (CSRF защита)
if (state !== expectedState) {
  throw new Error('Invalid state parameter');
}
```

### Шаг 4: Обмен code на токены

Обменяйте authorization code на токены:

**Endpoint:** `POST /sso/token`

⚠️ **ВАЖНО:** Этот endpoint принимает данные в формате `application/x-www-form-urlencoded` (Form данные), а не JSON. Это соответствует стандарту OAuth 2.0.

**Запрос:**

Content-Type: `application/x-www-form-urlencoded`

```
grant_type=authorization_code
&code=authorization_code_from_redirect
&client_id=your_client_id
&client_secret=your_client_secret
&redirect_uri=https://myplatform.com/callback
```

**Ответ:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Иван Иванов",
    ...
  }
}
```

**Пример (JavaScript):**

```javascript
const response = await fetch('http://localhost:8000/sso/token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code: code,
    client_id: 'your_client_id',
    client_secret: 'your_client_secret',
    redirect_uri: 'https://myplatform.com/callback'
  })
});

const tokens = await response.json();
// Сохраните токены в localStorage или cookies
localStorage.setItem('accessToken', tokens.access_token);
localStorage.setItem('refreshToken', tokens.refresh_token);
```

---

## QR Code Flow

QR Code Flow предназначен для случаев, когда пользователь должен авторизоваться с другого устройства (например, со смартфона на публичном экране).

### Шаг 1: Создание QR сессии

Платформа запрашивает создание QR-кода:

**Endpoint:** `POST /sso/qr/initiate`

**Запрос:**
```json
{
  "client_id": "your_client_id",
  "scope": "openid profile email"
}
```

**Ответ:**
```json
{
  "device_code": "long_device_code_string",
  "user_code": "ABCD-1234",
  "verification_uri": "http://localhost:3000/sso/qr/verify",
  "verification_uri_complete": "http://localhost:3000/sso/qr/verify?user_code=ABCD-1234",
  "expires_in": 600,
  "interval": 5
}
```

### Шаг 2: Отображение QR-кода

Сгенерируйте QR-код из `verification_uri_complete` и покажите его пользователю.

**Пример (JavaScript):**

```javascript
const response = await fetch('http://localhost:8000/sso/qr/initiate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    client_id: 'your_client_id',
    scope: 'openid profile email'
  })
});

const qrData = await response.json();

// Используйте библиотеку для генерации QR (например, qrcode.js)
QRCode.toCanvas(document.getElementById('qr-canvas'), qrData.verification_uri_complete);

// Покажите user_code пользователю
document.getElementById('user-code').textContent = qrData.user_code;
```

### Шаг 3: Polling статуса

Платформа опрашивает статус авторизации каждые 5 секунд:

**Endpoint:** `POST /sso/qr/token`

**Запрос:**
```json
{
  "device_code": "device_code_from_initiate",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

**Ответ (pending):**
```json
{
  "status": "pending",
  "message": "Ожидание авторизации... Пожалуйста, отсканируйте QR-код и войдите."
}
```

**Ответ (authorized):**
```json
{
  "status": "authorized",
  "message": "Авторизация успешна!",
  "access_token": "eyJhbGc...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "email": "user@example.com",
    ...
  }
}
```

**Пример polling:**

```javascript
async function pollQRStatus(deviceCode) {
  const maxAttempts = 120; // 10 минут (120 * 5 секунд)
  let attempts = 0;

  const poll = async () => {
    attempts++;
    
    const response = await fetch('http://localhost:8000/sso/qr/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        device_code: deviceCode,
        client_id: 'your_client_id',
        client_secret: 'your_client_secret'
      })
    });

    const data = await response.json();

    if (data.status === 'authorized') {
      // Авторизация успешна, сохраните токены
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      window.location.href = '/dashboard';
    } else if (data.status === 'pending' && attempts < maxAttempts) {
      // Продолжаем polling
      setTimeout(poll, 5000);
    } else {
      // Истекло время или ошибка
      alert('QR-код истек. Пожалуйста, отсканируйте новый QR-код.');
    }
  };

  poll();
}
```

---

## Code Flow (Magic Link / OTP)

Code Flow позволяет пользователю войти через 6-цифровой код, который показывается в Life SSO.

### Шаг 1: Запрос кода

Пользователь вводит email или имя на платформе:

**Endpoint:** `POST /sso/code/request`

**Запрос:**
```json
{
  "client_id": "your_client_id",
  "identifier": "user@example.com"
}
```

**Ответ:**
```json
{
  "code_id": "unique_code_id",
  "code": null,
  "message": "Код отправлен. Откройте Life SSO и перейдите в раздел 'Коды для входа на платформы' чтобы увидеть ваш код.",
  "expires_in": 300
}
```

⚠️ **ВАЖНО:** Код **не** возвращается платформе. Пользователь должен открыть Life SSO и увидеть код там.

### Шаг 2: Пользователь видит код в Life SSO

Пользователь открывает Life SSO (например, на своем телефоне) и видит 6-цифровой код на странице `/sso/codes`.

### Шаг 3: Пользователь вводит код на платформе

Платформа показывает поле для ввода кода, пользователь вводит его.

### Шаг 4: Проверка кода и получение токенов

Платформа проверяет код:

**Endpoint:** `POST /sso/code/verify`

**Запрос:**
```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "code_id": "code_id_from_request",
  "code": "123456"
}
```

**Ответ:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "email": "user@example.com",
    ...
  }
}
```

**Пример:**

```javascript
// Шаг 1: Запрос кода
const requestResponse = await fetch('http://localhost:8000/sso/code/request', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    client_id: 'your_client_id',
    identifier: userEmail
  })
});

const { code_id, message } = await requestResponse.json();
alert(message); // "Откройте Life SSO..."

// Шаг 4: Проверка кода
const userCode = prompt('Введите 6-цифровой код из Life SSO:');

const verifyResponse = await fetch('http://localhost:8000/sso/code/verify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    client_id: 'your_client_id',
    client_secret: 'your_client_secret',
    code_id: code_id,
    code: userCode
  })
});

const tokens = await verifyResponse.json();
localStorage.setItem('accessToken', tokens.access_token);
```

---

## Управление клиентами

### Создание клиента

**Endpoint:** `POST /sso/clients`

**Требуется:** Авторизация (Bearer token)

**Запрос:**
```json
{
  "name": "My Platform",
  "redirect_uri": "https://myplatform.com/callback",
  "allowed_scopes": "openid profile email"
}
```

**Ответ:**
```json
{
  "client_id": "abc123...",
  "client_secret": "xyz789...",
  "name": "My Platform",
  "redirect_uri": "https://myplatform.com/callback",
  "allowed_scopes": "openid profile email",
  "message": "Клиент успешно создан. Сохраните client_secret!"
}
```

### Список клиентов

**Endpoint:** `GET /sso/clients`

**Требуется:** Авторизация (Bearer token)

**Ответ:**
```json
[
  {
    "id": 1,
    "client_id": "abc123...",
    "name": "My Platform",
    "redirect_uri": "https://myplatform.com/callback",
    "allowed_scopes": "openid profile email",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00"
  }
]
```

---

## Схемы данных

### User (Пользователь)

```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "phone": "+79001234567",
  "birth_date": "1990-01-01",
  "is_active": true,
  "is_biometric_verified": false,
  "created_at": "2025-01-01T00:00:00"
}
```

### OAuthClient

```json
{
  "id": 1,
  "client_id": "abc123...",
  "name": "My Platform",
  "redirect_uri": "https://myplatform.com/callback",
  "allowed_scopes": "openid profile email",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00"
}
```

### OAuthTokenResponse

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { ... }
}
```

---

## Коды ошибок

### HTTP Status Codes

| Код | Описание |
|-----|----------|
| `200` | Успешный запрос |
| `302` | Редирект (Authorization Code Flow) |
| `400` | Неверный запрос (неверные параметры) |
| `401` | Неавторизован (неверный client_secret или токен) |
| `403` | Доступ запрещен (пользователь неактивен) |
| `404` | Не найдено (пользователь не найден) |
| `429` | Превышен лимит запросов (rate limiting) |
| `500` | Внутренняя ошибка сервера |

### Детали ошибок

Все ошибки возвращаются в формате:

```json
{
  "detail": "Описание ошибки"
}
```

**Примеры ошибок:**

```json
{
  "detail": "Неверный или истекший authorization code"
}
```

```json
{
  "detail": "Превышен лимит запросов. Попробуйте через минуту."
}
```

```json
{
  "detail": "Запрошенный scope не разрешен для этого клиента"
}
```

---

## Безопасность

### Rate Limiting

Life SSO применяет rate limiting для защиты от злоупотреблений:

- **Authorization Code Flow (email/password):** 5 попыток в 5 минут по email
- **Authorization Code Flow (биометрия):** 5 попыток в 5 минут по IP адресу
- **Token Exchange:** 10 запросов/минуту по client_id
- **QR Initiate:** 10 запросов/минуту по client_id
- **Code Request:** 1 запрос/минуту по identifier (email/name)
- **Code Verify:** 20 запросов/минуту по client_id

При превышении лимита возвращается `429 Too Many Requests`.

### Валидация redirect_uri

`redirect_uri` в запросах должен **точно совпадать** с зарегистрированным при создании клиента.

### Scope Validation

Запрошенные scope проверяются против `allowed_scopes` клиента. Если клиент не разрешил какой-то scope, запрос будет отклонен.

### CSRF Protection

Используйте параметр `state` в Authorization Code Flow для защиты от CSRF атак:

1. Генерируйте случайную строку перед редиректом
2. Сохраняйте её (например, в session)
3. Проверяйте при получении authorization code

```javascript
// Генерация state
const state = generateRandomString();
sessionStorage.setItem('oauth_state', state);

// Проверка state
const urlParams = new URLSearchParams(window.location.search);
const receivedState = urlParams.get('state');
const savedState = sessionStorage.getItem('oauth_state');

if (receivedState !== savedState) {
  throw new Error('CSRF attack detected!');
}
```

### Хранение client_secret

⚠️ **НИКОГДА** не храните `client_secret` в клиентском коде (JavaScript, мобильное приложение).

`client_secret` должен использоваться только на **бэкенде** вашей платформы.

---

## Примеры интеграции

### JavaScript (Frontend + Backend)

#### Frontend (Authorization Code Flow)

```javascript
// 1. Редирект на Life SSO
function initiateLogin() {
  const state = generateRandomString();
  sessionStorage.setItem('oauth_state', state);
  
  const params = new URLSearchParams({
    client_id: 'your_client_id',
    redirect_uri: 'https://myplatform.com/callback',
    state: state,
    scope: 'openid profile email'
  });
  
  window.location.href = `http://localhost:8000/sso/authorize?${params}`;
}

// 2. Обработка callback
async function handleCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');
  
  // Проверка state
  const savedState = sessionStorage.getItem('oauth_state');
  if (state !== savedState) {
    throw new Error('Invalid state');
  }
  
  // Обмен code на токены (делайте это на бэкенде!)
  const response = await fetch('/api/auth/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code })
  });
  
  const tokens = await response.json();
  localStorage.setItem('accessToken', tokens.access_token);
  window.location.href = '/dashboard';
}
```

#### Backend (Node.js)

```javascript
// POST /api/auth/token
app.post('/api/auth/token', async (req, res) => {
  const { code } = req.body;
  
  // Обмен code на токены (используем Form данные, не JSON!)
  const response = await fetch('http://localhost:8000/sso/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      client_id: process.env.CLIENT_ID,
      client_secret: process.env.CLIENT_SECRET, // Только на бэкенде!
      redirect_uri: 'https://myplatform.com/callback'
    })
  });
  
  const tokens = await response.json();
  res.json(tokens);
});
```

### Python

```python
import requests

# Authorization Code Flow
def exchange_code_for_tokens(code, client_id, client_secret, redirect_uri):
    # Используем data вместо json для Form данных
    response = requests.post(
        'http://localhost:8000/sso/token',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri
        }
    )
    return response.json()

# QR Code Flow
def initiate_qr(client_id):
    response = requests.post(
        'http://localhost:8000/sso/qr/initiate',
        json={
            'client_id': client_id,
            'scope': 'openid profile email'
        }
    )
    return response.json()

def poll_qr_status(device_code, client_id, client_secret):
    response = requests.post(
        'http://localhost:8000/sso/qr/token',
        json={
            'device_code': device_code,
            'client_id': client_id,
            'client_secret': client_secret
        }
    )
    return response.json()
```

---

## FAQ

### Q: Какой flow выбрать?

**A:** 
- **Authorization Code Flow** — для веб-приложений
- **QR Code Flow** — для публичных экранов / TV
- **Code Flow** — когда пользователь не может открыть Life SSO напрямую

### Q: Можно ли использовать один client_id для нескольких платформ?

**A:** Нет, каждая платформа должна иметь свой `client_id` и `client_secret`.

### Q: Как обновить access token?

**A:** Используйте refresh token через endpoint `/refresh` (если реализован) или запросите новый через OAuth flow.

### Q: Что делать если authorization code истек?

**A:** Попросите пользователя пройти авторизацию заново.

### Q: Можно ли изменить redirect_uri после создания клиента?

**A:** В текущей версии — нет. Нужно создать нового клиента с новым redirect_uri.

### Q: Как проверить, что токен валиден?

**A:** Используйте endpoint `/me` или проверьте токен на вашей платформе (валидация JWT).

---

## Поддержка

Если у вас возникли вопросы или проблемы:

1. Проверьте эту документацию
2. Проверьте логи вашей платформы
3. Обратитесь к администратору Life SSO

---

**Версия документации:** 1.0  
**Дата обновления:** 2025-01-01


