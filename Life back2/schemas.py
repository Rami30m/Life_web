from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# ===== Схемы для User =====
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    phone: str
    birth_date: str
    password: str

class UserResponse(UserBase):
    id: int
    phone: str
    birth_date: str
    is_active: bool
    is_biometric_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===== Схемы для аутентификации =====
class UserLogin(BaseModel):
    """Схема для логина пользователя"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Схема ответа с токенами"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Время жизни access токена в секундах
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    """Схема для обновления access токена"""
    refresh_token: str

class AccessTokenResponse(BaseModel):
    """Схема ответа при обновлении access токена"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# ===== Схемы для биометрии =====
class BiometricRegister(BaseModel):
    """Схема для регистрации биометрических данных"""
    descriptor: list[float]  # Массив из 128 чисел (face descriptor)
    timestamp: str
    version: str

class BiometricResponse(BaseModel):
    """Схема ответа после регистрации биометрии"""
    message: str
    user_id: int
    verified: bool = True
    user: UserResponse  # Возвращаем обновленного пользователя

class BiometricLogin(BaseModel):
    """Схема для входа по биометрии"""
    descriptor: list[float]  # Массив из 128 чисел (face descriptor)
    timestamp: str
    version: str

# Схемы для Item
class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: int

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    is_available: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ===== Схемы для SSO =====

# Схемы для OAuth клиентов (платформы)
class OAuthClientCreate(BaseModel):
    """Схема для создания нового OAuth клиента"""
    name: str  # Название платформы
    redirect_uri: str  # URL для редиректа после авторизации
    allowed_scopes: Optional[str] = "openid profile email"  # Разрешенные scope

class OAuthClientResponse(BaseModel):
    """Схема ответа с данными OAuth клиента"""
    id: int
    client_id: str
    name: str
    redirect_uri: str
    allowed_scopes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class OAuthClientCreateResponse(BaseModel):
    """Схема ответа при создании клиента (включает secret)"""
    client_id: str
    client_secret: str  # Показываем только при создании
    name: str
    redirect_uri: str
    allowed_scopes: Optional[str]
    message: str = "Клиент успешно создан. Сохраните client_secret, он больше не будет показан!"

# Схемы для Authorization Code Flow
class OAuthAuthorizeRequest(BaseModel):
    """Схема для запроса авторизации (GET параметры)"""
    client_id: str
    redirect_uri: str
    response_type: str = "code"
    state: Optional[str] = None
    scope: Optional[str] = "openid profile email"

class OAuthTokenRequest(BaseModel):
    """Схема для обмена code на токены"""
    grant_type: str = "authorization_code"
    code: str
    client_id: str
    client_secret: str
    redirect_uri: str

class OAuthTokenResponse(BaseModel):
    """Схема ответа при обмене code на токены"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

# Схемы для QR Code Flow
class QRInitiateRequest(BaseModel):
    """Схема для запроса QR сессии"""
    client_id: str
    scope: Optional[str] = "openid profile email"

class QRInitiateResponse(BaseModel):
    """Схема ответа при инициализации QR"""
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int = 5  # Интервал для polling в секундах

class QRTokenRequest(BaseModel):
    """Схема для проверки статуса QR"""
    device_code: str
    client_id: str
    client_secret: str

class QRTokenResponse(BaseModel):
    """Схема ответа при проверке QR статуса"""
    status: str  # pending или authorized
    message: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    user: Optional[UserResponse] = None

# Схемы для Code Flow (Magic Link / OTP)
class CodeRequestRequest(BaseModel):
    """Схема для запроса кода"""
    client_id: str
    identifier: str  # email или имя пользователя
    redirect_uri: Optional[str] = None

class CodeRequestResponse(BaseModel):
    """Схема ответа при запросе кода"""
    code_id: str
    code: Optional[str] = None  # НЕ возвращаем код - он показывается на Life SSO
    message: str
    expires_in: int

class CodeVerifyRequest(BaseModel):
    """Схема для проверки кода"""
    client_id: str
    client_secret: str
    code_id: str
    code: str

class CodeVerifyResponse(BaseModel):
    """Схема ответа при проверке кода"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


