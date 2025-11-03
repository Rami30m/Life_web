# Скрипт для тестирования регистрации платформы через Life SSO

Этот скрипт автоматизирует процесс тестирования регистрации платформы и входа через Life SSO.

**Доступны две версии:**
- Python: `test_sso_platform_registration.py` (рекомендуется)
- Node.js: `test_sso_platform_registration.js`

## Что делает скрипт:

1. **Регистрирует платформу** через API `/sso/clients`
2. **Открывает браузер** с формой авторизации Life SSO
3. **Ждет входа пользователя** через Life SSO
4. **Получает authorization code** через callback
5. **Обменивает code на токены** через `/sso/token`
6. **Показывает результат** (успешно/не успешно)

## Требования:

### Python версия:
- Python 3.6 или выше
- Библиотека `requests` (`pip install requests`)
- Запущенный backend Life SSO (`Life back2`) на `http://localhost:8000`
- Зарегистрированный пользователь в системе Life SSO

### Node.js версия:
- Node.js (версия 12 или выше)
- Запущенный backend Life SSO (`Life back2`) на `http://localhost:8000`
- Зарегистрированный пользователь в системе Life SSO

## Установка:

### Python:
```bash
pip install requests
```

### Node.js:
```bash
# Скрипт использует только встроенные модули Node.js
# Никаких дополнительных установок не требуется
```

## Настройка:

### Python (`test_sso_platform_registration.py`):

1. **Данные для входа** (строки ~29-30):
```python
LOGIN_EMAIL = 'test@example.com'  # Замените на ваш email
LOGIN_PASSWORD = 'test123'  # Замените на ваш пароль
```

2. **Данные платформы** (строки ~19-24):
```python
PLATFORM_DATA = {
    'name': 'Тестовая Платформа',
    'redirect_uri': f'{PLATFORM_URL}/callback',
    'allowed_scopes': 'openid profile email'
}
```

### Node.js (`test_sso_platform_registration.js`):

1. **Данные для входа** (строки ~76-77):
```javascript
email: 'test@example.com', // Замените на ваш email
password: 'test123' // Замените на ваш пароль
```

2. **Данные платформы** (строки ~19-23):
```javascript
const platformData = {
  name: 'Тестовая Платформа',
  redirect_uri: `${PLATFORM_URL}/callback`,
  allowed_scopes: 'openid profile email'
};
```

## Запуск:

### Python:
```bash
python test_sso_platform_registration.py
# или
python3 test_sso_platform_registration.py
```

### Node.js:
```bash
node test_sso_platform_registration.js
```

## Процесс работы:

1. Скрипт запускает локальный сервер на порту 3001 для callback
2. Регистрирует платформу через API (с автоматическим входом если требуется)
3. Открывает браузер с формой авторизации Life SSO
4. **Вы должны войти** в открывшемся браузере
5. После успешного входа вы будете перенаправлены обратно
6. Скрипт автоматически обменивает полученный код на токены
7. Показывает результат в консоли

## Пример вывода при успехе:

```
🚀 Запуск тестового скрипта для регистрации платформы через Life SSO

📝 Шаг 1: Регистрация платформы...
✅ Платформа успешно зарегистрирована!
   📛 Название: Тестовая Платформа
   🆔 Client ID: client_abc123...
   🔑 Client Secret: secret_xyz789...
   🔗 Redirect URI: http://localhost:3001/callback

🌐 Шаг 2: Создан callback сервер на http://localhost:3001/callback

🌐 Шаг 3: Открываем форму авторизации в браузере...
👤 Пожалуйста, войдите в Life SSO в открывшемся браузере.

📥 Получен callback от Life SSO:
   Code: auth_code_123...
   State: test_state_123

🔄 Шаг 4: Обмен authorization code на токены...
✅ Токены успешно получены!
   🔑 Access Token: eyJhbGciOiJIUzI1NiIs...
   🔄 Refresh Token: refresh_token_abc...
   👤 Пользователь: Иван Иванов (ivan@example.com)
   ⏰ Expires In: 3600 секунд

============================================================
🎉 РЕГИСТРАЦИЯ И ВХОД НА ПЛАТФОРМУ ПРОШЛИ УСПЕШНО!
============================================================

📊 Итоговые данные:
   📛 Платформа: Тестовая Платформа
   🆔 Client ID: client_abc123
   👤 Пользователь: Иван Иванов (ivan@example.com)
   🔑 Access Token получен: ✅
   🔄 Refresh Token получен: ✅

✅ Тест пройден успешно!
```

## Устранение проблем:

### Ошибка "Требуется авторизация"
- Убедитесь, что данные для входа (email/password) правильные
- Проверьте, что пользователь существует в системе

### Ошибка "Порт 3001 уже занят"
- Измените `PLATFORM_PORT` в скрипте на другой порт
- Или закройте другое приложение, использующее порт 3001

### Браузер не открывается
- Откройте URL вручную (скрипт выведет его в консоль)

### Ошибка обмена токенов
- Проверьте, что код не истек (коды живут 10 минут)
- Убедитесь, что `client_secret` правильный
- Проверьте, что backend работает на `localhost:8000`

## Примечания:

- Скрипт автоматически останавливается после завершения
- Все данные (client_id, client_secret, токены) выводятся в консоль
- Callback сервер автоматически закрывается после получения кода

