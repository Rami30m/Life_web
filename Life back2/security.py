"""
Модуль безопасности для SSO: rate limiting, валидация, логирование
"""

from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import Request, HTTPException, status
from collections import defaultdict
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sso_security")

# ===== RATE LIMITING (простая реализация в памяти) =====
# В продакшене лучше использовать Redis или другой внешний store

_rate_limit_store: Dict[str, List[datetime]] = defaultdict(list)

def check_rate_limit(
    identifier: str,
    max_requests: int = 10,
    time_window: int = 60  # секунды
) -> bool:
    """
    Проверяет rate limit для идентификатора (IP, email, client_id)
    
    Args:
        identifier: Уникальный идентификатор (IP адрес, email, client_id)
        max_requests: Максимальное количество запросов
        time_window: Окно времени в секундах
    
    Returns:
        True если запрос разрешен, False если превышен лимит
    """
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=time_window)
    
    # Очищаем старые записи
    _rate_limit_store[identifier] = [
        req_time for req_time in _rate_limit_store[identifier]
        if req_time > window_start
    ]
    
    # Проверяем лимит
    if len(_rate_limit_store[identifier]) >= max_requests:
        return False
    
    # Добавляем текущий запрос
    _rate_limit_store[identifier].append(now)
    return True

def get_client_ip(request: Request) -> str:
    """Получает IP адрес клиента из запроса"""
    if request.client:
        return request.client.host
    return "unknown"

# ===== ВАЛИДАЦИЯ REDIRECT_URI =====

def validate_redirect_uri(client_redirect_uri: str, provided_uri: str) -> bool:
    """
    Валидирует redirect_uri
    
    Args:
        client_redirect_uri: Зарегистрированный redirect_uri клиента
        provided_uri: URI предоставленный в запросе
    
    Returns:
        True если URI валиден
    """
    # Простая проверка: provided_uri должен начинаться с client_redirect_uri
    # В продакшене можно добавить более сложную логику
    if not provided_uri or not client_redirect_uri:
        return False
    
    # Нормализуем URI (убираем trailing slash)
    client_uri = client_redirect_uri.rstrip('/')
    provided_uri_norm = provided_uri.rstrip('/')
    
    # Проверяем что provided URI начинается с client URI
    return provided_uri_norm.startswith(client_uri)

# ===== ВАЛИДАЦИЯ SCOPE =====

def validate_scope(requested_scope: str, allowed_scope: Optional[str]) -> bool:
    """
    Валидирует scope запроса
    
    Args:
        requested_scope: Запрошенный scope (например "openid profile email")
        allowed_scope: Разрешенный scope клиента (хранится в БД, может быть через пробелы или запятую)
    
    Returns:
        True если все запрошенные scope разрешены
    """
    if not allowed_scope:
        # Если у клиента нет ограничений, разрешаем все
        return True
    
    if not requested_scope:
        # Если scope не запрошен, разрешаем
        return True
    
    # Разбиваем requested_scope по пробелам
    requested_scopes = set(scope.strip() for scope in requested_scope.split())
    
    # Разбиваем allowed_scope - поддерживаем и пробелы, и запятые
    # Сначала пробуем через запятую, если нет - через пробелы
    if ',' in allowed_scope:
        allowed_scopes = set(scope.strip() for scope in allowed_scope.split(','))
    else:
        allowed_scopes = set(scope.strip() for scope in allowed_scope.split())
    
    # Проверяем что все запрошенные scope разрешены
    return requested_scopes.issubset(allowed_scopes)

# ===== ЛОГИРОВАНИЕ SSO СОБЫТИЙ =====

def log_sso_event(
    event_type: str,
    user_id: Optional[int] = None,
    client_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict] = None,
    success: bool = True
):
    """
    Логирует SSO событие
    
    Args:
        event_type: Тип события (authorize, token_exchange, qr_initiate, code_request, etc.)
        user_id: ID пользователя (если известен)
        client_id: ID OAuth клиента
        ip_address: IP адрес клиента
        details: Дополнительные детали
        success: Успешность операции
    """
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "client_id": client_id,
        "ip_address": ip_address,
        "success": success,
        "details": details or {}
    }
    
    if success:
        logger.info(f"SSO Event: {event_type}", extra=log_data)
    else:
        logger.warning(f"SSO Event Failed: {event_type}", extra=log_data)

# ===== DECORATOR ДЛЯ RATE LIMITING =====

def rate_limit_decorator(max_requests: int = 10, time_window: int = 60, identifier_key: str = "ip"):
    """
    Декоратор для добавления rate limiting к эндпоинтам
    
    Args:
        max_requests: Максимальное количество запросов
        time_window: Окно времени в секундах
        identifier_key: Ключ для идентификации ("ip", "email", "client_id")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            # Ищем Request в аргументах
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                # Определяем идентификатор
                if identifier_key == "ip":
                    identifier = get_client_ip(request)
                elif identifier_key == "email" and "email" in kwargs:
                    identifier = kwargs["email"]
                elif identifier_key == "client_id" and "client_id" in kwargs:
                    identifier = kwargs["client_id"]
                else:
                    identifier = get_client_ip(request)
                
                # Проверяем rate limit
                if not check_rate_limit(identifier, max_requests, time_window):
                    log_sso_event(
                        event_type="rate_limit_exceeded",
                        ip_address=get_client_ip(request),
                        success=False,
                        details={"identifier": identifier}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Превышен лимит запросов. Попробуйте через {time_window} секунд."
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


