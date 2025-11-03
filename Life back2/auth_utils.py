from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import secrets
import bcrypt
import os
import base64
import json
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# Загружаем переменные окружения из .env файла
load_dotenv()

# ===== КОНФИГУРАЦИЯ =====
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Ключ для AES шифрования (должен быть 32 байта для AES-256)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", SECRET_KEY[:32].encode('utf-8') if len(SECRET_KEY) >= 32 else (SECRET_KEY * 2)[:32].encode('utf-8'))

# ===== ФУНКЦИИ ДЛЯ ПАРОЛЕЙ =====
def hash_password(password: str) -> str:
    """Хеширует пароль используя bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля хешу"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

# ===== ФУНКЦИИ ДЛЯ JWT ТОКЕНОВ =====
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT access токен
    
    Args:
        data: Данные для включения в токен (user_id, email, и т.д.)
        expires_delta: Время жизни токена (по умолчанию 30 минут)
    
    Returns:
        JWT токен в виде строки
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token() -> tuple[str, datetime]:
    """
    Создает refresh токен (случайная строка) и дату истечения
    
    Returns:
        Tuple (токен, дата_истечения)
    """
    # Генерируем случайный токен (64 символа)
    token = secrets.token_urlsafe(48)
    
    # Устанавливаем дату истечения
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    return token, expires_at

def hash_token(token: str) -> str:
    """
    Хеширует refresh токен для хранения в БД
    
    Args:
        token: Токен для хеширования
    
    Returns:
        Хешированный токен
    """
    return bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_token_hash(plain_token: str, hashed_token: str) -> bool:
    """
    Проверяет соответствие токена хешу
    
    Args:
        plain_token: Оригинальный токен
        hashed_token: Хешированный токен из БД
    
    Returns:
        True если токен совпадает, иначе False
    """
    return bcrypt.checkpw(plain_token.encode('utf-8'), hashed_token.encode('utf-8'))

def decode_access_token(token: str) -> Optional[dict]:
    """
    Декодирует и проверяет JWT access токен
    
    Args:
        token: JWT токен
    
    Returns:
        Декодированные данные из токена или None если токен невалиден
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Проверяем тип токена
        if payload.get("type") != "access":
            return None
        
        return payload
    
    except JWTError:
        return None

def get_user_from_token(token: str) -> Optional[int]:
    """
    Извлекает user_id из JWT токена
    
    Args:
        token: JWT токен
    
    Returns:
        user_id или None если токен невалиден
    """
    payload = decode_access_token(token)
    if payload:
        return payload.get("user_id")
    return None

# ===== ФУНКЦИИ ДЛЯ AES ШИФРОВАНИЯ =====

def encrypt_aes(data: str) -> str:
    """
    Шифрует данные с помощью AES-256-CBC
    
    Args:
        data: Строка для шифрования
    
    Returns:
        Base64 строка (IV + зашифрованные данные)
    """
    # Генерируем случайный IV (Initialization Vector)
    iv = secrets.token_bytes(16)  # 16 байт для AES
    
    # Создаем cipher
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    # Добавляем padding (AES требует кратность 16 байтам)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode('utf-8')) + padder.finalize()
    
    # Шифруем
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    # Возвращаем IV + зашифрованные данные в base64
    return base64.b64encode(iv + encrypted_data).decode('utf-8')

def decrypt_aes(encrypted_data: str) -> str:
    """
    Расшифровывает данные с помощью AES-256-CBC
    
    Args:
        encrypted_data: Base64 строка (IV + зашифрованные данные)
    
    Returns:
        Расшифрованная строка
    """
    # Декодируем из base64
    encrypted_bytes = base64.b64decode(encrypted_data)
    
    # Извлекаем IV (первые 16 байт)
    iv = encrypted_bytes[:16]
    encrypted_content = encrypted_bytes[16:]
    
    # Создаем cipher
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    
    # Расшифровываем
    decrypted_padded = decryptor.update(encrypted_content) + decryptor.finalize()
    
    # Убираем padding
    unpadder = padding.PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
    
    return decrypted_data.decode('utf-8')

def encrypt_face_descriptor(descriptor: list[float]) -> str:
    """
    Шифрует face descriptor для хранения в БД
    
    Args:
        descriptor: Массив из 128 чисел
    
    Returns:
        Зашифрованная base64 строка
    """
    descriptor_json = json.dumps(descriptor)
    return encrypt_aes(descriptor_json)

def decrypt_face_descriptor(encrypted_descriptor: str) -> list[float]:
    """
    Расшифровывает face descriptor из БД
    
    Args:
        encrypted_descriptor: Зашифрованная base64 строка
    
    Returns:
        Массив из 128 чисел
    """
    descriptor_json = decrypt_aes(encrypted_descriptor)
    return json.loads(descriptor_json)

# ===== ФУНКЦИИ ДЛЯ OAUTH CLIENT_SECRET =====

def hash_client_secret(secret: str) -> str:
    """
    Хеширует client_secret для OAuth клиентов используя bcrypt
    (аналогично hash_password, но для ясности отдельная функция)
    """
    secret_bytes = secret.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(secret_bytes, salt)
    return hashed.decode('utf-8')

def verify_client_secret(plain_secret: str, hashed_secret: str) -> bool:
    """
    Проверяет соответствие client_secret хешу
    """
    secret_bytes = plain_secret.encode('utf-8')
    hashed_bytes = hashed_secret.encode('utf-8')
    return bcrypt.checkpw(secret_bytes, hashed_bytes)

def generate_client_id() -> str:
    """
    Генерирует уникальный client_id для OAuth клиента
    """
    return secrets.token_urlsafe(32)[:50]  # 50 символов URL-safe

def generate_client_secret() -> str:
    """
    Генерирует случайный client_secret для OAuth клиента
    """
    return secrets.token_urlsafe(48)  # 64 символа URL-safe

# ===== ФУНКЦИИ ДЛЯ OAUTH AUTHORIZATION CODE =====

def generate_authorization_code() -> str:
    """
    Генерирует уникальный authorization code для OAuth 2.0 flow
    Code должен быть одноразовым и иметь ограниченное время жизни (10 минут)
    """
    return secrets.token_urlsafe(32)  # 43 символа URL-safe (256 бит энтропии)

def generate_state() -> str:
    """
    Генерирует случайный state параметр для защиты от CSRF атак
    """
    return secrets.token_urlsafe(24)  # 32 символа URL-safe

# ===== ФУНКЦИИ ДЛЯ OAUTH DEVICE CODE (QR FLOW) =====

def generate_device_code() -> str:
    """
    Генерирует длинный device_code для QR flow
    Используется для проверки статуса авторизации
    """
    return secrets.token_urlsafe(32)  # 43 символа URL-safe (256 бит энтропии)

def generate_user_code() -> str:
    """
    Генерирует короткий user_code для отображения пользователю
    Формат: XXXX-XXXX (8 символов, разделенных дефисом)
    Пример: "ABCD-1234"
    """
    # Генерируем 8 случайных символов (A-Z, 0-9)
    import string
    chars = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(chars) for _ in range(8))
    # Форматируем как XXXX-XXXX
    return f"{code[:4]}-{code[4:]}"

# ===== ФУНКЦИИ ДЛЯ OAUTH VERIFICATION CODE (CODE FLOW) =====

def generate_verification_code() -> str:
    """
    Генерирует 6-цифровой код для входа (Magic Link / OTP)
    Формат: 6 цифр (000000-999999)
    Пример: "123456"
    """
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def generate_code_id() -> str:
    """
    Генерирует уникальный code_id для идентификации сессии кода
    Используется для привязки кода к конкретному запросу
    """
    return secrets.token_urlsafe(24)  # 32 символа URL-safe



