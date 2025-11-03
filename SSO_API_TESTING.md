# 🧪 Тестирование SSO API

## Этап 1: Управление OAuth клиентами

## Способы тестирования

### 1. Python скрипт (автоматическое тестирование)

**Файл:** `test_sso_api.py`

**Запуск:**
```bash
pip install requests
python test_sso_api.py
```

**Что тестирует:**
- ✅ Регистрация/вход пользователя
- ✅ Создание OAuth клиента (`POST /sso/clients`)
- ✅ Получение списка клиентов (`GET /sso/clients`)
- ✅ Проверка защиты эндпоинтов (без токена)

---

### 2. Swagger UI (интерактивное тестирование)

**Откройте в браузере:**
```
http://localhost:8000/docs
```

**Шаги:**
1. Сначала авторизуйтесь через `/login` или `/register`
2. Скопируйте полученный `access_token`
3. Нажмите кнопку **"Authorize"** вверху страницы
4. Введите: `Bearer <ваш_access_token>`
5. Теперь можете тестировать `/sso/clients` эндпоинты

---

### 3. Postman/Insomnia (REST клиенты)

#### Настройка коллекции:

**Переменные:**
- `base_url`: `http://localhost:8000`
- `access_token`: (будет заполнен после логина)

#### Тест 1: Регистрация пользователя
```
POST {{base_url}}/register
Content-Type: application/json

{
  "full_name": "Test User",
  "email": "test@sso.com",
  "phone": "+79991234567",
  "birth_date": "1990-01-01",
  "password": "TestPass123!"
}
```

**Сохраните `access_token` из ответа в переменную!**

#### Тест 2: Создание OAuth клиента
```
POST {{base_url}}/sso/clients
Authorization: Bearer {{access_token}}
Content-Type: application/json

{
  "name": "My Platform",
  "redirect_uri": "https://myplatform.com/callback",
  "allowed_scopes": "openid profile email"
}
```

**⚠️ ВАЖНО:** Сохраните `client_id` и `client_secret` из ответа!

#### Тест 3: Список OAuth клиентов
```
GET {{base_url}}/sso/clients
Authorization: Bearer {{access_token}}
```

#### Тест 4: Проверка защиты (без токена - должна быть 401)
```
GET {{base_url}}/sso/clients
```

---

### 4. cURL команды

#### Регистрация:
```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@sso.com",
    "phone": "+79991234567",
    "birth_date": "1990-01-01",
    "password": "TestPass123!"
  }'
```

**Сохраните `access_token` из ответа!**

#### Создание OAuth клиента:
```bash
curl -X POST "http://localhost:8000/sso/clients" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Platform",
    "redirect_uri": "https://platform.com/callback",
    "allowed_scopes": "openid profile email"
  }'
```

#### Список клиентов:
```bash
curl -X GET "http://localhost:8000/sso/clients" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Ожидаемые ответы

### ✅ Успешное создание OAuth клиента (200):
```json
{
  "client_id": "abc123xyz...",
  "client_secret": "secret456...",
  "name": "Test Platform",
  "redirect_uri": "https://platform.com/callback",
  "allowed_scopes": "openid profile email",
  "message": "Клиент успешно создан. Сохраните client_secret, он больше не будет показан!"
}
```

### ✅ Список OAuth клиентов (200):
```json
[
  {
    "id": 1,
    "client_id": "abc123xyz...",
    "name": "Test Platform",
    "redirect_uri": "https://platform.com/callback",
    "allowed_scopes": "openid profile email",
    "is_active": true,
    "created_at": "2025-11-01T12:00:00",
    "updated_at": "2025-11-01T12:00:00"
  }
]
```

**Обратите внимание:** `client_secret` НЕ возвращается в списке!

### ❌ Ошибка без авторизации (401):
```json
{
  "detail": "Не предоставлен токен авторизации"
}
```

---

## Чеклист тестирования

- [ ] Применить миграцию: `alembic upgrade head`
- [ ] Запустить сервер: `uvicorn main:app --reload`
- [ ] Регистрация пользователя работает
- [ ] Создание OAuth клиента работает (требует токен)
- [ ] Получение списка клиентов работает (требует токен)
- [ ] `client_secret` возвращается только при создании
- [ ] `client_secret` НЕ возвращается в списке
- [ ] Без токена возвращается 401
- [ ] С неверным токеном возвращается 401

---

## Отладка

### Проблема: "Не предоставлен токен авторизации"
**Решение:** Убедитесь, что используете заголовок:
```
Authorization: Bearer <ваш_access_token>
```

### Проблема: "Невалидный или истекший токен"
**Решение:** 
- Токен истек (30 минут). Войдите заново через `/login`
- Или обновите токен через `/refresh`

### Проблема: Ошибка подключения
**Решение:** Убедитесь, что сервер запущен:
```bash
cd "Life back2"
uvicorn main:app --reload
```

---

**Готово! Теперь можете тестировать SSO API.**

