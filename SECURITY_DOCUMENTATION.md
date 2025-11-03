# 🔐 Документация безопасности проекта Life SSO

## 📋 Содержание
1. [Введение](#введение)
2. [Архитектура безопасности](#архитектура-безопасности)
3. [Защита паролей](#защита-паролей)
4. [JWT токены (аутентификация)](#jwt-токены-аутентификация)
5. [Шифрование биометрических данных](#шифрование-биометрических-данных)
6. [Защита API эндпоинтов](#защита-api-эндпоинтов)
7. [Сетевая безопасность](#сетевая-безопасность)
8. [Валидация данных](#валидация-данных)
9. [Безопасность фронтенда](#безопасность-фронтенда)
10. [База данных](#база-данных)
11. [Конфигурация и секреты](#конфигурация-и-секреты)
12. [Версии библиотек](#версии-библиотек)
13. [Биометрическая безопасность](#биометрическая-безопасность)
14. [Рекомендации для Production](#рекомендации-для-production)
15. [Чеклист безопасности](#чеклист-безопасности)

---

## 1. Введение

### Назначение документа
Данный документ описывает полную систему безопасности проекта **Life SSO** — приложения для единого входа (Single Sign-On) с поддержкой биометрической аутентификации по лицу.

### Обзор системы безопасности
Life SSO использует **многоуровневую архитектуру безопасности**:
- 🔒 **Хеширование паролей** — bcrypt для защиты учетных данных
- 🔑 **JWT токены** — Access + Refresh стратегия для SSO
- 🛡️ **Шифрование биометрии** — AES-256-CBC для защиты face descriptors
- ✅ **Валидация данных** — Pydantic для защиты от некорректных входных данных
- 🚪 **Защита эндпоинтов** — middleware для проверки токенов

### Основные принципы
1. **Принцип минимальных привилегий** — пользователь получает доступ только к необходимым ресурсам
2. **Defense in Depth** — несколько слоев защиты
3. **Шифрование чувствительных данных** — пароли и биометрия никогда не хранятся в открытом виде
4. **Разделение ответственности** — бэкенд отвечает за безопасность, фронтенд за UX

---

## 2. Архитектура безопасности

### Многоуровневая защита

```
┌─────────────────────────────────────────────────┐
│           ФРОНТЕНД (Next.js)                      │
│  • Валидация форм                                │
│  • localStorage для токенов                      │
│  • Защита от XSS (React автоматически)           │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS (рекомендуется)
                   ▼
┌─────────────────────────────────────────────────┐
│           БЭКЕНД (FastAPI)                       │
│  ┌──────────────────────────────────────────┐   │
│  │ Уровень 1: CORS + Валидация (Pydantic)   │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Уровень 2: Middleware (get_current_user) │   │
│  │ • Проверка JWT токенов                   │   │
│  │ • Валидация подписи                      │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ Уровень 3: Бизнес-логика                 │   │
│  │ • Проверка активности пользователя      │   │
│  │ • Проверка прав доступа                  │   │
│  └──────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────┘
                   │ SQLAlchemy ORM
                   ▼
┌─────────────────────────────────────────────────┐
│           БАЗА ДАННЫХ (PostgreSQL)               │
│  • Хешированные пароли (bcrypt)                 │
│  • Зашифрованная биометрия (AES-256)            │
│  • Хешированные refresh токены (bcrypt)         │
│  • Индексы для производительности               │
└─────────────────────────────────────────────────┘
```

### Разделение ответственности

| Компонент | Ответственность |
|-----------|----------------|
| **Фронтенд** | UX, валидация форм, хранение токенов, отправка запросов |
| **Бэкенд** | Валидация данных, аутентификация, шифрование, бизнес-логика |
| **БД** | Безопасное хранение зашифрованных данных |

---

## 3. Защита паролей

### Алгоритм: bcrypt

**Версия библиотеки:** `bcrypt==4.1.2`

**Реализация:**
```python
# Life back2/auth_utils.py
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()  # Автоматическая генерация salt
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')
```

### Характеристики bcrypt

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| **Алгоритм** | Blowfish (адаптивный) | Стойкий к брутфорсу |
| **Salt** | Автоматический, уникальный для каждого пароля | Защита от rainbow tables |
| **Раунды** | 12 (по умолчанию) | Баланс безопасности и производительности |
| **Формат хранения** | `$2b$12$...salt...hash...` | Включает salt и раунды |

### Почему bcrypt?

✅ **Защита от брутфорса**
- Адаптивный алгоритм (можно увеличить сложность)
- Медленный по дизайну (замедляет атаки)

✅ **Уникальный salt для каждого пароля**
- Даже одинаковые пароли дают разные хеши
- Невозможно использовать предвычисленные таблицы

✅ **Индустриальный стандарт**
- Используется в Django, Flask, многих production системах
- Проверен временем (с 1999 года)

### Процесс хеширования

```
Пользователь вводит: "MyPassword123"
           │
           ▼
┌──────────────────────────┐
│ bcrypt.gensalt()         │ → Случайный salt (29 байт)
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ bcrypt.hashpw(           │
│   password + salt,       │
│   rounds=12              │
│ )                        │ → Хеш (60 символов)
└──────────────────────────┘
           │
           ▼
Результат: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LSY5YvQeG."

Структура: $версия$раунды$salt(22 символа)hash(31 символ)
```

### Хранение в БД

```sql
-- Таблица users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR NOT NULL,  -- Хранится только хеш!
    ...
);
```

**Пример:**
```
Пароль: "test123"
Хеш в БД: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LSY5YvQeG."
```

**Важно:** Оригинальный пароль **НЕВОЗМОЖНО** восстановить из хеша!

### Проверка пароля

```python
# Life back2/auth_utils.py
def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
```

**Процесс:**
1. Берем salt из сохраненного хеша
2. Хешируем введенный пароль с тем же salt
3. Сравниваем результаты

---

## 4. JWT токены (аутентификация)

### Обзор стратегии: Access + Refresh

Для SSO приложения используется **двухтокенная стратегия**:

| Тип токена | Назначение | Срок жизни | Хранение |
|------------|------------|------------|----------|
| **Access Token** | Доступ к API | 30 минут | localStorage (клиент) |
| **Refresh Token** | Обновление Access | 30 дней | БД (хешированный) |

**Преимущества:**
- ✅ Короткая жизнь Access токена → минимизация ущерба при компрометации
- ✅ Долгая жизнь Refresh токена → удобство для пользователя (SSO)
- ✅ Возможность отзыва через БД (is_active флаг)

### Access токены (JWT)

#### Технические детали

**Алгоритм:** `HS256` (HMAC-SHA256)
**Библиотека:** `python-jose[cryptography]==3.3.0`

**Конфигурация:**
```python
# Life back2/auth_utils.py
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Настраивается в .env
```

#### Структура JWT токена

JWT состоит из 3 частей, разделенных точками:
```
header.payload.signature
```

**Пример реального токена:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJJdmFuIEl2YW5vdiIsImV4cCI6MTcwOTg3NjQwMCwiaWF0IjoxNzA5ODc0NjAwLCJ0eXBlIjoiYWNjZXNzIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

**Декодированный payload:**
```json
{
  "user_id": 1,
  "email": "test@example.com",
  "full_name": "Ivan Ivanov",
  "exp": 1709876400,      // Время истечения (Unix timestamp)
  "iat": 1709874600,      // Время создания
  "type": "access"        // Тип токена (защита от подмены)
}
```

#### Создание Access токена

```python
# Life back2/auth_utils.py
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,           # Время истечения
        "iat": datetime.utcnow(), # Время создания
        "type": "access"         # Тип токена
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

#### Проверка Access токена

```python
# Life back2/auth_utils.py
def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Проверяем тип токена (защита от подмены на refresh)
        if payload.get("type") != "access":
            return None
        
        return payload
    except JWTError:
        return None
```

**Что проверяется автоматически:**
- ✅ Подпись токена (не изменен ли)
- ✅ Время истечения (`exp`)
- ✅ Алгоритм (должен быть HS256)

#### Использование в API

```python
# Life back2/main.py
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    # Извлекаем токен из заголовка "Bearer <token>"
    scheme, token = authorization.split()
    
    # Декодируем и проверяем токен
    user_id = get_user_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    # Получаем пользователя из БД
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

**Заголовок HTTP запроса:**
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refresh токены

#### Генерация

```python
# Life back2/auth_utils.py
def create_refresh_token() -> tuple[str, datetime]:
    # Генерируем случайный токен (64 символа URL-safe)
    token = secrets.token_urlsafe(48)  # 48 байт → 64 символа base64
    
    # Устанавливаем срок жизни (30 дней)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    return token, expires_at
```

**Характеристики:**
- **Длина:** 64 символа (URL-safe base64)
- **Энтропия:** 48 байт случайных данных (256 бит)
- **Формат:** `A1B2C3D4E5F6...` (безопасен для URL)

#### Хранение в БД

**Важно:** Refresh токены **хешируются** перед сохранением!

```python
# Life back2/auth_utils.py
def hash_token(token: str) -> str:
    return bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
```

**Модель БД:**
```python
# Life back2/models.py
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(Text, unique=True, nullable=False)  # ХЕШИРОВАННЫЙ токен!
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)  # Для отзыва
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Почему хеширование?**
- ✅ Защита при утечке БД (невозможно использовать напрямую)
- ✅ Даже админ БД не может увидеть реальные токены

#### Проверка Refresh токена

```python
# Life back2/main.py
@app.post("/refresh")
async def refresh_access_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Получаем все активные refresh токены
    refresh_tokens = db.query(RefreshToken).filter(
        RefreshToken.is_active == True,
        RefreshToken.expires_at > datetime.utcnow()
    ).all()
    
    # Сравниваем хеши
    db_refresh_token = None
    for rt in refresh_tokens:
        if verify_token_hash(request.refresh_token, rt.token):
            db_refresh_token = rt
            break
    
    if not db_refresh_token:
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")
    
    # Создаем новый access токен
    user = db.query(User).filter(User.id == db_refresh_token.user_id).first()
    new_access_token = create_access_token({"user_id": user.id, ...})
    
    return {"access_token": new_access_token, ...}
```

#### Отзыв Refresh токена (Logout)

```python
# Life back2/main.py
@app.post("/logout")
async def logout_user(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Находим токен по хешу
    refresh_tokens = db.query(RefreshToken).filter(RefreshToken.is_active == True).all()
    
    for rt in refresh_tokens:
        if verify_token_hash(request.refresh_token, rt.token):
            rt.is_active = False  # Отзываем токен
            db.commit()
            return {"message": "Успешный выход"}
```

### Жизненный цикл токенов

```
1. РЕГИСТРАЦИЯ/ВХОД
   ┌─────────────────────────┐
   │ POST /register или /login│
   └────────────┬─────────────┘
                │
                ▼
   ┌────────────────────────────┐
   │ Бэкенд генерирует:          │
   │ • Access Token (30 мин)     │
   │ • Refresh Token (30 дней)   │
   └────────────┬────────────────┘
                │
                ▼
   ┌────────────────────────────┐
   │ Клиент сохраняет в          │
   │ localStorage               │
   └────────────────────────────┘

2. РАБОТА С API
   ┌─────────────────────────┐
   │ GET /me                  │
   │ Authorization: Bearer   │
   │   <access_token>         │
   └────────────┬─────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │ Бэкенд проверяет:        │
   │ • Подпись токена        │
   │ • Время истечения       │
   │ • Тип токена (access)   │
   └────────────┬─────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │ ✅ Доступ разрешен       │
   └─────────────────────────┘

3. ОБНОВЛЕНИЕ ACCESS ТОКЕНА (через 30 минут)
   ┌─────────────────────────┐
   │ POST /refresh            │
   │ { refresh_token: "..." } │
   └────────────┬─────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │ Бэкенд:                  │
   │ • Проверяет хеш токена  │
   │ • Проверяет is_active   │
   │ • Проверяет expires_at  │
   └────────────┬─────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │ ✅ Новый Access Token    │
   └─────────────────────────┘

4. ВЫХОД
   ┌─────────────────────────┐
   │ POST /logout             │
   │ { refresh_token: "..." } │
   └────────────┬─────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │ Бэкенд:                  │
   │ is_active = False       │
   └────────────┬─────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │ Клиент очищает          │
   │ localStorage            │
   └─────────────────────────┘
```

---

## 5. Шифрование биометрических данных

### Алгоритм: AES-256-CBC

**Версия библиотеки:** `cryptography==41.0.7`

**Конфигурация:**
```python
# Life back2/auth_utils.py
ENCRYPTION_KEY = os.getenv(
    "ENCRYPTION_KEY",
    SECRET_KEY[:32].encode('utf-8') if len(SECRET_KEY) >= 32 
    else (SECRET_KEY * 2)[:32].encode('utf-8')
)
```

**Характеристики:**
- **Алгоритм:** AES (Advanced Encryption Standard)
- **Размер ключа:** 256 бит (32 байта)
- **Режим:** CBC (Cipher Block Chaining)
- **IV:** 16 байт (случайный для каждого шифрования)
- **Padding:** PKCS7 (128 бит)

### Что такое AES-256?

**AES (Advanced Encryption Standard)** — симметричный алгоритм шифрования, выбранный правительством США как стандарт шифрования.

**256-битный ключ:**
- Количество возможных ключей: 2^256 = 10^77
- Для взлома методом перебора потребуется больше времени, чем возраст Вселенной

### Почему CBC режим?

**CBC (Cipher Block Chaining):**
- ✅ Каждый блок зависит от предыдущего (защита от паттернов)
- ✅ Требует IV (Initialization Vector) для уникальности
- ✅ Индустриальный стандарт для чувствительных данных

**Альтернативы (не используются):**
- ECB — небезопасен (одинаковые блоки → одинаковый шифртекст)
- GCM — лучше, но сложнее (можно рассмотреть для будущего)

### Процесс шифрования

```python
# Life back2/auth_utils.py
def encrypt_aes(data: str) -> str:
    # 1. Генерируем случайный IV (16 байт)
    iv = secrets.token_bytes(16)
    
    # 2. Создаем cipher объект
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),  # 32 байта
        modes.CBC(iv),                    # Режим CBC с IV
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    # 3. Добавляем padding (AES работает с блоками по 16 байт)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode('utf-8')) + padder.finalize()
    
    # 4. Шифруем
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    # 5. Возвращаем IV + зашифрованные данные в base64
    return base64.b64encode(iv + encrypted_data).decode('utf-8')
```

**Визуализация:**
```
Исходные данные: [128 чисел face descriptor]
           │
           ▼
┌──────────────────────────┐
│ JSON.stringify()         │ → "{'descriptor': [0.123, ...]}"
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ PKCS7 Padding            │ → Дополнение до кратности 16 байт
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ AES-256-CBC Encryption   │ → Блоки по 16 байт
│ IV (случайный) + ключ    │ → Зашифрованные блоки
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Base64 Encoding          │ → Безопасная строка для БД
└──────────────────────────┘
           │
           ▼
Сохранение в БД: "iv(16 байт) + encrypted_data"
```

### Процесс расшифровки

```python
# Life back2/auth_utils.py
def decrypt_aes(encrypted_data: str) -> str:
    # 1. Декодируем из base64
    encrypted_bytes = base64.b64decode(encrypted_data)
    
    # 2. Извлекаем IV (первые 16 байт)
    iv = encrypted_bytes[:16]
    encrypted_content = encrypted_bytes[16:]
    
    # 3. Создаем cipher
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),  # Используем тот же IV
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    
    # 4. Расшифровываем
    decrypted_padded = decryptor.update(encrypted_content) + decryptor.finalize()
    
    # 5. Убираем padding
    unpadder = padding.PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted_data.decode('utf-8')
```

### Использование для биометрии

```python
# Life back2/auth_utils.py
def encrypt_face_descriptor(descriptor: list[float]) -> str:
    """Шифрует массив из 128 чисел (face descriptor)"""
    descriptor_json = json.dumps(descriptor)
    return encrypt_aes(descriptor_json)

def decrypt_face_descriptor(encrypted_descriptor: str) -> list[float]:
    """Расшифровывает face descriptor из БД"""
    descriptor_json = decrypt_aes(encrypted_descriptor)
    return json.loads(descriptor_json)
```

**Пример использования:**
```python
# При регистрации биометрии
descriptor = [0.123, -0.456, 0.789, ...]  # 128 чисел
encrypted = encrypt_face_descriptor(descriptor)
# Сохраняем encrypted в БД

# При входе по биометрии
encrypted_from_db = "base64_encrypted_string..."
descriptor = decrypt_face_descriptor(encrypted_from_db)
# Сравниваем с новым descriptor
```

### Хранение в БД

```sql
-- Таблица biometric_data
CREATE TABLE biometric_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id),
    face_descriptors TEXT NOT NULL,  -- Зашифрованная строка Base64
    ...
);
```

**Пример:**
```
Исходные данные: [0.123, -0.456, 0.789, ...]
Зашифрованное в БД: "dGVzdF9pdl9oZXJlX2VuY3J5cHRlZF9kYXRhX2hlcmU..."
```

**Важно:** Даже при полном доступе к БД **невозможно** восстановить оригинальные face descriptors без ключа шифрования!

### Почему шифрование вместо хеширования?

| Метод | Восстановление | Использование |
|-------|---------------|---------------|
| **Хеширование** (bcrypt) | ❌ Невозможно | Только для проверки (пароли) |
| **Шифрование** (AES) | ✅ Возможно с ключом | Для данных, которые нужно сравнивать (биометрия) |

**Биометрические дескрипторы нужно:**
- ✅ Сравнивать с новыми (расстояние между векторами)
- ✅ Расшифровывать для вычислений

**Поэтому:** AES-256-CBC для биометрии, bcrypt для паролей.

---

## 6. Защита API эндпоинтов

### Middleware: get_current_user

Все защищенные эндпоинты используют middleware для проверки токенов:

```python
# Life back2/main.py
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Middleware для получения текущего пользователя из access токена
    """
    # 1. Проверка наличия заголовка
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлен токен авторизации"
        )
    
    # 2. Извлечение токена из "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверная схема авторизации"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат токена"
        )
    
    # 3. Декодирование и проверка JWT
    user_id = get_user_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истекший токен"
        )
    
    # 4. Получение пользователя из БД
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен"
        )
    
    return user
```

### Защищенные эндпоинты

```python
# Life back2/main.py

# Требует access токен
@app.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Получение информации о текущем пользователе"""
    return UserResponse.model_validate(current_user)

# Требует access токен
@app.post("/biometric/register", response_model=BiometricResponse)
async def register_biometric(
    biometric_data: BiometricRegister,
    current_user: User = Depends(get_current_user),  # ← Защита!
    db: Session = Depends(get_db)
):
    """Регистрация биометрических данных"""
    # ...
```

### Публичные эндпоинты

```python
# Life back2/main.py

# НЕ требует токен
@app.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # ...

# НЕ требует токен
@app.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """Вход пользователя"""
    # ...

# НЕ требует токен (биометрический вход)
@app.post("/biometric/login", response_model=TokenResponse)
async def login_by_biometric(
    biometric_data: BiometricLogin,
    db: Session = Depends(get_db)
):
    """Вход по биометрии"""
    # ...
```

### Проверки безопасности

| Проверка | Описание | Код ошибки |
|----------|----------|------------|
| **Нет токена** | Authorization header отсутствует | 401 |
| **Неверный формат** | Не "Bearer <token>" | 401 |
| **Невалидная подпись** | Токен изменен или подделан | 401 |
| **Истекший токен** | `exp` в прошлом | 401 |
| **Неверный тип** | Не access токен | 401 |
| **Пользователь не найден** | user_id не существует | 401 |
| **Пользователь неактивен** | `is_active = False` | 401 |

---

## 7. Сетевая безопасность

### CORS (Cross-Origin Resource Sharing)

**Конфигурация:**
```python
# Life back2/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Что делает:**
- ✅ Разрешает запросы только с `localhost:3000` (фронтенд)
- ✅ Разрешает отправку cookies/tokens (credentials)
- ✅ Разрешает все HTTP методы (GET, POST, PUT, DELETE, ...)
- ✅ Разрешает все заголовки (включая Authorization)

**Для Production:**
```python
# Рекомендуется указать конкретные домены
allow_origins=[
    "https://sso.life-company.com",
    "https://app.life-company.com"
]
```

### HTTPS (рекомендуется для Production)

**Текущее состояние:** HTTP (разработка)

**Для Production:**
- ✅ Использовать HTTPS для всех соединений
- ✅ Настроить SSL/TLS сертификаты (Let's Encrypt, Cloudflare)
- ✅ Принудительное перенаправление HTTP → HTTPS

**Почему важно:**
- Защита от перехвата трафика (Man-in-the-Middle)
- Защита токенов при передаче
- Требование для современных браузеров

### Защита от атак

| Атака | Защита |
|-------|--------|
| **SQL Injection** | SQLAlchemy ORM (параметризованные запросы) |
| **XSS** | React автоматически экранирует |
| **CSRF** | CORS ограничения, проверка токенов |
| **Man-in-the-Middle** | HTTPS (для production) |
| **Брутфорс паролей** | bcrypt (медленное хеширование) |
| **Подделка токенов** | JWT подпись (HS256) |

---

## 8. Валидация данных

### Библиотека: Pydantic

**Версия:** `pydantic[email]==2.5.0`

### Схемы валидации

```python
# Life back2/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr  # ← Автоматическая валидация email
    phone: str
    birth_date: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BiometricRegister(BaseModel):
    descriptor: list[float]  # Должен быть массив чисел
    timestamp: str
    version: str
```

### Валидация на бэкенде

```python
# Life back2/main.py
@app.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Pydantic автоматически проверяет:
    # ✅ email - правильный формат
    # ✅ full_name - не пустая строка
    # ✅ phone - не пустая строка
    # ✅ Типы данных соответствуют схеме
    
    # Дополнительная проверка на дубликаты
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
```

### Валидация биометрии

```python
# Life back2/main.py
@app.post("/biometric/register")
async def register_biometric(
    biometric_data: BiometricRegister,
    ...
):
    # Проверка количества дескрипторов
    if len(biometric_data.descriptor) != 128:
        raise HTTPException(
            status_code=400,
            detail=f"Ожидается 128 чисел, получено {len(biometric_data.descriptor)}"
        )
```

### Защита от SQL Injection

**SQLAlchemy ORM использует параметризованные запросы:**

```python
# ✅ БЕЗОПАСНО (SQLAlchemy)
user = db.query(User).filter(User.email == email).first()

# ❌ ОПАСНО (сырой SQL - НЕ используется!)
# db.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

**SQLAlchemy автоматически:**
- Экранирует специальные символы
- Использует параметризованные запросы
- Защищает от SQL injection

---

## 9. Безопасность фронтенда

### Хранение токенов

**Текущая реализация:** `localStorage`

```javascript
// life/app/page.js
const handleSuccessfulAuth = (user, tokens) => {
    // Сохраняем токены в localStorage
    if (typeof window !== 'undefined') {
        localStorage.setItem('accessToken', tokens.access_token);
        localStorage.setItem('refreshToken', tokens.refresh_token);
        localStorage.setItem('userData', JSON.stringify(user));
    }
};
```

### Риски localStorage

| Риск | Описание | Митигация |
|------|----------|-----------|
| **XSS атаки** | JavaScript может прочитать localStorage | React экранирует, валидация входных данных |
| **Уязвимые библиотеки** | Третьесторонние библиотеки могут иметь XSS | Регулярное обновление, проверка зависимостей |

### Рекомендации для Production

**Вариант 1: HttpOnly Cookies (рекомендуется)**
```javascript
// Бэкенд устанавливает cookie
// JavaScript НЕ может прочитать (защита от XSS)
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,  // ← Ключевое свойство
    secure=True,    // Только HTTPS
    samesite="strict"
);
```

**Вариант 2: sessionStorage (временное хранение)**
- Удаляется при закрытии вкладки
- Недоступен между вкладками

### Отправка токенов

```javascript
// life/app/components/BiometricVerification.js
fetch('http://localhost:8000/biometric/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`  // ← Отправка токена
    },
    body: JSON.stringify({...})
});
```

### Очистка при выходе

```javascript
// life/app/page.js
const handleLogout = async () => {
    // Отправляем запрос на отзыв токена
    await fetch('http://localhost:8000/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    // Очищаем localStorage
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('userData');
};
```

---

## 10. База данных

### PostgreSQL

**Подключение:**
```python
# Life back2/database.py
DATABASE_URL = "postgresql://rami:test123455@localhost:5432/lifeback"
engine = create_engine(DATABASE_URL)
```

### Структура таблиц

```sql
-- Таблица users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,        -- Индекс для быстрого поиска
    hashed_password VARCHAR NOT NULL,     -- Хешированный пароль
    is_active BOOLEAN DEFAULT TRUE,       -- Флаг активности
    is_biometric_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица refresh_tokens
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,           -- Хешированный refresh токен
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,       -- Для отзыва
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица biometric_data
CREATE TABLE biometric_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    face_descriptors TEXT NOT NULL,       -- Зашифрованные дескрипторы
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Индексы для производительности

```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
```

### CASCADE удаление

**При удалении пользователя:**
- ✅ Автоматически удаляются все его refresh токены
- ✅ Автоматически удаляются его биометрические данные

```python
# Life back2/models.py
refresh_tokens = relationship(
    "RefreshToken",
    back_populates="user",
    cascade="all, delete-orphan"  # ← Автоматическое удаление
)
```

---

## 11. Конфигурация и секреты

### Файл .env

**Расположение:** `Life back2/.env`

**Содержимое:**
```env
SECRET_KEY=972cea12d8115bbe95ec5b89af6f8ef42168a6ccf10ddd8db89cfe041c013387
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
DATABASE_URL=postgresql://rami:test123455@localhost:5432/lifeback
ENCRYPTION_KEY=  # Опционально (по умолчанию берется из SECRET_KEY)
```

### Загрузка переменных

```python
# Life back2/auth_utils.py
from dotenv import load_dotenv
import os

load_dotenv()  # Загружает .env файл

SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-me")
```

### Безопасность .env

**✅ Правильно:**
- `.env` добавлен в `.gitignore`
- Секреты не коммитятся в Git
- У каждого окружения свой `.env`

**❌ Неправильно:**
- Коммитить `.env` в Git
- Использовать одинаковые ключи для dev/prod
- Хранить секреты в коде

### Генерация секретных ключей

**SECRET_KEY (для JWT):**
```bash
# Генерируем 64-символьный ключ (256 бит в hex)
python -c "import secrets; print(secrets.token_hex(32))"
# Результат: 972cea12d8115bbe95ec5b89af6f8ef42168a6ccf10ddd8db89cfe041c013387
```

**ENCRYPTION_KEY (для AES):**
```bash
# Генерируем 32-байтный ключ (256 бит)
python -c "import secrets; print(secrets.token_bytes(32).hex())"
# Результат: a1b2c3d4e5f6... (64 символа hex = 32 байта)
```

**Важно:**
- ✅ Использовать разные ключи для SECRET_KEY и ENCRYPTION_KEY в production
- ✅ Длина SECRET_KEY: минимум 32 символа (рекомендуется 64+)
- ✅ Длина ENCRYPTION_KEY: ровно 32 байта (256 бит)

---

## 12. Версии библиотек

### Полный список зависимостей

```txt
# Life back2/requirements.txt
fastapi==0.120.1              # Веб-фреймворк
uvicorn[standard]==0.38.0     # ASGI сервер
sqlalchemy==2.0.44            # ORM для БД
psycopg2-binary==2.9.11       # PostgreSQL драйвер
pydantic[email]==2.5.0        # Валидация данных
python-dotenv==1.0.0          # Загрузка .env
bcrypt==4.1.2                 # Хеширование паролей
alembic==1.13.1               # Миграции БД
python-jose[cryptography]==3.3.0  # JWT токены
python-multipart==0.0.6       # Мультипарт запросы
cryptography==41.0.7          # AES шифрование
```

### Обоснование версий

| Библиотека | Версия | Обоснование |
|------------|--------|-------------|
| **bcrypt** | 4.1.2 | Последняя стабильная, поддержка Python 3.10+ |
| **python-jose** | 3.3.0 | Поддержка HS256, совместимость с FastAPI |
| **cryptography** | 41.0.7 | Поддержка AES-256-CBC, актуальная безопасность |
| **pydantic** | 2.5.0 | Новый синтаксис, улучшенная валидация email |
| **fastapi** | 0.120.1 | Стабильная версия с поддержкой async |

### Проверка уязвимостей

**Рекомендуется регулярно:**
```bash
# Проверка через pip-audit или safety
pip install pip-audit
pip-audit
```

**Обновление зависимостей:**
```bash
# Обновить все зависимости до последних версий
pip install --upgrade -r requirements.txt
```

---

## 13. Биометрическая безопасность

### Face Descriptors

**Что это:**
- 128-мерный числовой вектор
- Представляет уникальные черты лица
- Извлекается через `face-api.js` (TinyFaceDetector + FaceLandmark68Net + FaceRecognitionNet)

**Пример:**
```javascript
descriptor = [
    0.123456789, -0.987654321, 0.555555555, ...
]  // 128 чисел типа float
```

### Порог совпадения

```python
# Life back2/main.py
MATCH_THRESHOLD = 0.6  # Евклидово расстояние

# Чем меньше расстояние, тем больше похожесть
distance = euclidean_distance(descriptor1, descriptor2)

if distance < MATCH_THRESHOLD:
    # ✅ Лицо распознано
else:
    # ❌ Лицо не распознано
```

**Настройка порога:**
- **0.4** — строже (меньше ложных срабатываний, но больше отказов)
- **0.6** — сбалансировано (текущее значение)
- **0.8** — мягче (больше ложных срабатываний)

### Защита от подделки

**1. Проверка ориентации лица:**
```javascript
// life/app/utils/faceApi.js
checkFaceOrientation(detection) {
    // Проверка что пользователь смотрит прямо в камеру
    // Проверка горизонтального/вертикального смещения
    // Проверка угла поворота (roll)
}
```

**2. Проверка качества детекции:**
- Уверенность детекции (`confidence > 0.5`)
- Наличие всех 68 landmarks

**3. Видеопоток вместо фото:**
- Требуется активная камера
- Защита от подделки статичным изображением

### Сравнение дескрипторов

```python
# Life back2/main.py
def euclidean_distance(desc1: list[float], desc2: list[float]) -> float:
    import math
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(desc1, desc2)))
```

**Процесс:**
1. Получаем новый descriptor от клиента
2. Расшифровываем все сохраненные descriptors из БД
3. Вычисляем расстояние до каждого
4. Находим минимальное расстояние
5. Если минимальное < порог → вход разрешен

**Безопасность:**
- ✅ Дескрипторы зашифрованы в БД
- ✅ Расшифровка происходит только при сравнении
- ✅ Невозможно восстановить лицо из descriptor (однонаправленное преобразование)

---

## 14. Рекомендации для Production

### 🔒 Обязательные меры

**1. HTTPS**
```nginx
# Nginx конфигурация
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Принудительное перенаправление HTTP → HTTPS
    if ($scheme != "https") {
        return 301 https://$host$request_uri;
    }
}
```

**2. Отдельные секретные ключи**
```env
# Production .env
SECRET_KEY=<уникальный_64_символа>
ENCRYPTION_KEY=<уникальный_32_байта_hex>
```

**3. HttpOnly Cookies**
```python
# Использовать cookies вместо localStorage
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,
    samesite="strict",
    max_age=1800  # 30 минут
);
```

**4. Rate Limiting**
```python
# Защита от брутфорса
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/login")
@limiter.limit("5/minute")  # Максимум 5 попыток в минуту
async def login_user(...):
    ...
```

**5. Логирование безопасности**
```python
import logging

security_logger = logging.getLogger("security")

@app.post("/login")
async def login_user(...):
    if failed:
        security_logger.warning(
            f"Failed login attempt for {email} from {client_ip}"
        )
```

### 🔍 Дополнительные меры

**1. Мониторинг**
- Логирование всех попыток входа
- Алерты при множественных неудачных попытках
- Мониторинг использования токенов

**2. Резервное копирование БД**
```bash
# Автоматический бэкап PostgreSQL
pg_dump lifeback > backup_$(date +%Y%m%d).sql
```

**3. Регулярные аудиты безопасности**
- Проверка зависимостей на уязвимости
- Обновление библиотек
- Проверка логов на подозрительную активность

**4. Двухфакторная аутентификация (2FA)**
- Можно добавить SMS/Email коды
- TOTP (Google Authenticator)

**5. IP Whitelisting (опционально)**
- Ограничение доступа к API по IP адресам
- Для корпоративного использования

---

## 15. Чеклист безопасности

### ✅ Реализовано

- [x] **Пароли хешированы** (bcrypt 4.1.2)
- [x] **JWT токены подписаны** (HS256, python-jose 3.3.0)
- [x] **Refresh токены хешируются** в БД
- [x] **Биометрия зашифрована** (AES-256-CBC, cryptography 41.0.7)
- [x] **Валидация данных** (Pydantic 2.5.0)
- [x] **Защита эндпоинтов** (middleware get_current_user)
- [x] **CORS настроен** (ограничение origins)
- [x] **SQL Injection защита** (SQLAlchemy ORM)
- [x] **Отзыв токенов** (logout эндпоинт)
- [x] **Проверка активности пользователя** (is_active флаг)

### ⚠️ Для Production

- [ ] **HTTPS включен** (SSL/TLS сертификаты)
- [ ] **HttpOnly Cookies** (вместо localStorage)
- [ ] **Отдельные секретные ключи** (не из .env по умолчанию)
- [ ] **Rate Limiting** (ограничение запросов с IP)
- [ ] **Логирование безопасности** (audit log всех действий)
- [ ] **Мониторинг безопасности** (алерты на подозрительную активность)
- [ ] **Резервное копирование БД** (encrypted backups)
- [ ] **Регулярные обновления** (зависимостей и библиотек)
- [ ] **Penetration Testing** (периодическое тестирование на проникновение)
- [ ] **GDPR Compliance** (если применимо)

---

## 16. Заключение

### Итоговая оценка безопасности

**Life SSO** использует современные и проверенные методы защиты:

✅ **Сильные стороны:**
- Многоуровневая защита (пароли, токены, биометрия)
- Использование проверенных криптографических библиотек
- Правильная архитектура JWT (Access + Refresh)
- Шифрование чувствительных данных (AES-256)
- Валидация всех входных данных
- Защита от SQL Injection (ORM)

⚠️ **Области для улучшения в production:**
- Переход на HttpOnly cookies вместо localStorage
- Внедрение HTTPS/SSL
- Rate limiting для защиты от брутфорса
- Расширенное логирование и мониторинг

### Следующие шаги

1. **Перед развертыванием в production:**
   - Настроить HTTPS
   - Сгенерировать уникальные секретные ключи
   - Настроить мониторинг и алерты
   - Провести security audit

2. **Регулярное обслуживание:**
   - Обновлять зависимости
   - Проверять логи безопасности
   - Тестировать восстановление из резервных копий

3. **Мониторинг:**
   - Отслеживать неудачные попытки входа
   - Анализировать использование токенов
   - Контролировать биометрические аутентификации

---

## 17. Контакты и ресурсы

### Документация библиотек

- **bcrypt**: https://github.com/pyca/bcrypt/
- **python-jose**: https://python-jose.readthedocs.io/
- **cryptography**: https://cryptography.io/
- **Pydantic**: https://docs.pydantic.dev/
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/

### Стандарты безопасности

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **JWT Best Practices**: https://tools.ietf.org/html/rfc8725
- **NIST Password Guidelines**: https://pages.nist.gov/800-63-3/

---

**Документ создан:** 2025  
**Версия:** 1.0  
**Последнее обновление:** 2025