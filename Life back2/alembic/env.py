from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ===== ЭТАП 1: SSO ИНФРАСТРУКТУРА =====
# Импортируем наши модели для autogenerate
# Alembic использует эти импорты для автоматического определения изменений в БД
import sys
from os.path import dirname, abspath
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from database import Base
from models import (
    # Существующие модели (базовая аутентификация)
    User,              # Пользователи системы
    RefreshToken,      # Refresh токены для JWT
    BiometricData,     # Биометрические данные (face descriptors)
    Item,              # Пример модели (опционально)
    
    # ===== SSO МОДЕЛИ (ДОБАВЛЕНО НА ЭТАПЕ 1) =====
    # Эти модели нужны для реализации Single Sign-On (SSO) системы,
    # которая позволяет пользователям входить на другие платформы компании через Life SSO
    
    # 1. OAuthClient - Зарегистрированные платформы компании
    #    Хранит информацию о платформах, которые используют Life SSO для аутентификации
    #    - client_id: уникальный идентификатор платформы
    #    - client_secret: секретный ключ (хешированный) для проверки подлинности
    #    - redirect_uri: URL для возврата после авторизации
    #    - allowed_scopes: разрешенные области доступа (openid, profile, email)
    OAuthClient,
    
    # 2. OAuthAuthorizationCode - Коды авторизации (OAuth 2.0 Authorization Code Flow)
    #    Используется для метода входа через простую переадресацию
    #    - code: одноразовый код авторизации
    #    - expires_at: время истечения (обычно 10 минут)
    #    - is_used: флаг использования (код можно использовать только один раз)
    OAuthAuthorizationCode,
    
    # 3. OAuthDeviceCode - Device коды для QR-кода входа
    #    Используется для метода входа через сканирование QR-кода
    #    - device_code: длинный код для проверки статуса
    #    - user_code: короткий код для отображения пользователю (например, "ABCD-1234")
    #    - status: статус (pending, authorized, expired)
    #    - user_id: NULL пока не авторизован, заполняется после входа
    OAuthDeviceCode,
    
    # 4. OAuthVerificationCode - Коды для Magic Link / OTP входа
    #    Используется для метода входа по 6-цифровому коду
    #    - code_id: уникальный идентификатор сессии кода
    #    - code: 6-цифровой код (например, "123456")
    #    - attempts: количество попыток ввода (максимум 5)
    #    - is_used: флаг использования (код одноразовый)
    #    - expires_at: время истечения (обычно 5 минут)
    OAuthVerificationCode
)  # Импортируем все модели для autogenerate

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
