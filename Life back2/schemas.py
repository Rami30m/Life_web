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


