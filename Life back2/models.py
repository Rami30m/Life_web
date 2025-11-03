from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Модель пользователя
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    birth_date = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_biometric_verified = Column(Boolean, default=False)  # Флаг биометрической верификации
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    biometric_data = relationship("BiometricData", back_populates="user", cascade="all, delete-orphan", uselist=False)

# Модель refresh токенов для SSO
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, unique=True, nullable=False, index=True)  # Хешированный токен
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)  # Для отзыва токена
    device_info = Column(String, nullable=True)  # Информация об устройстве (опционально)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с пользователем
    user = relationship("User", back_populates="refresh_tokens")

# Модель биометрических данных
class BiometricData(Base):
    __tablename__ = "biometric_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    face_descriptors = Column(Text, nullable=False)  # JSON строка с хешированными дескрипторами
    confidence = Column(String, nullable=True)  # Уверенность детекции
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с пользователем
    user = relationship("User", back_populates="biometric_data")

# ===== SSO МОДЕЛИ =====

# Модель OAuth клиентов (платформы компании)
class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(100), unique=True, nullable=False, index=True)
    client_secret = Column(String(255), nullable=False)  # Хешированный secret
    name = Column(String(200), nullable=False)  # Название платформы
    redirect_uri = Column(Text, nullable=False)  # Куда возвращать после авторизации
    allowed_scopes = Column(Text, nullable=True)  # Разрешенные scope (через запятую)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    authorization_codes = relationship("OAuthAuthorizationCode", back_populates="client", cascade="all, delete-orphan")
    device_codes = relationship("OAuthDeviceCode", back_populates="client", cascade="all, delete-orphan")
    verification_codes = relationship("OAuthVerificationCode", back_populates="client", cascade="all, delete-orphan")

# Модель authorization codes (OAuth 2.0 Authorization Code Flow)
class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    client_id = Column(String(100), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    redirect_uri = Column(Text, nullable=False)
    scope = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    client = relationship("OAuthClient", back_populates="authorization_codes")
    user = relationship("User")

# Модель device codes (QR Code Flow)
class OAuthDeviceCode(Base):
    __tablename__ = "oauth_device_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String(100), unique=True, nullable=False, index=True)
    user_code = Column(String(20), unique=True, nullable=False, index=True)
    client_id = Column(String(100), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # NULL пока не авторизован
    scope = Column(Text, nullable=True)
    status = Column(String(20), default='pending')  # pending, authorized, expired
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    client = relationship("OAuthClient", back_populates="device_codes")
    user = relationship("User")

# Модель verification codes (Code Flow / Magic Link / OTP)
class OAuthVerificationCode(Base):
    __tablename__ = "oauth_verification_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code_id = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(10), nullable=False)  # 6-цифровой код
    client_id = Column(String(100), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    redirect_uri = Column(Text, nullable=True)
    attempts = Column(Integer, default=0)  # Количество попыток ввода
    max_attempts = Column(Integer, default=5)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    client = relationship("OAuthClient", back_populates="verification_codes")
    user = relationship("User")

# Пример модели элемента (можно удалить если не нужна)
class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String)
    price = Column(Integer)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


