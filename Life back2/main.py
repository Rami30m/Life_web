from fastapi import FastAPI, Depends, HTTPException, status, Header, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from schemas import (
    UserCreate, UserResponse, UserLogin, 
    TokenResponse, RefreshTokenRequest, AccessTokenResponse,
    BiometricRegister, BiometricResponse, BiometricLogin,
    # Схемы для SSO:
    OAuthClientCreate, OAuthClientResponse, OAuthClientCreateResponse,
    OAuthAuthorizeRequest, OAuthTokenRequest, OAuthTokenResponse,
    QRInitiateRequest, QRInitiateResponse, QRTokenRequest, QRTokenResponse,
    CodeRequestRequest, CodeRequestResponse, CodeVerifyRequest, CodeVerifyResponse
)
from models import User, RefreshToken, BiometricData, OAuthClient, OAuthAuthorizationCode, OAuthDeviceCode, OAuthVerificationCode
from database import get_db
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    hash_token, verify_token_hash,
    decode_access_token, get_user_from_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    encrypt_face_descriptor, decrypt_face_descriptor,
    # Функции для OAuth:
    hash_client_secret, verify_client_secret,
    generate_client_id, generate_client_secret,
    generate_authorization_code, generate_state,
    generate_device_code, generate_user_code,
    generate_verification_code, generate_code_id
)
from security import (
    check_rate_limit, get_client_ip, validate_redirect_uri,
    validate_scope, log_sso_event
)

# Таблицы создаются через Alembic миграции
app = FastAPI(title="Life SSO API", version="1.0.0")

# Настройка CORS для связи с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location"],  # Разрешаем доступ к Location header для редиректов
)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """
    Middleware для получения текущего пользователя из access токена
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлен токен авторизации"
        )
    
    # Извлекаем токен из заголовка "Bearer <token>"
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
    
    # Декодируем токен
    user_id = get_user_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истекший токен"
        )
    
    # Получаем пользователя из БД
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен"
        )
    
    return user

def create_tokens_for_user(user: User, db: Session) -> dict:
    """
    Создает access и refresh токены для пользователя
    """
    # Создаем access токен
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    )
    
    # Создаем refresh токен
    refresh_token_value, expires_at = create_refresh_token()
    
    # Хешируем refresh токен для хранения в БД
    hashed_refresh = hash_token(refresh_token_value)
    
    # Сохраняем refresh токен в БД
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=hashed_refresh,
        expires_at=expires_at,
        is_active=True
    )
    db.add(db_refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# ===== ЭНДПОИНТЫ =====
@app.get("/")
def read_root():
    return {
        "message": "Life SSO API",
        "version": "1.0.0",
        "endpoints": {
            "register": "/register",
            "login": "/login",
            "refresh": "/refresh",
            "logout": "/logout",
            "me": "/me"
        }
    }

@app.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя
    """
    # Выводим полученные данные в терминал
    print("\n" + "="*50)
    print("📥 ПОЛУЧЕНЫ ДАННЫЕ РЕГИСТРАЦИИ:")
    print("="*50)
    print(f"ФИО: {user.full_name}")
    print(f"Email: {user.email}")
    print(f"Телефон: {user.phone}")
    print(f"Дата рождения: {user.birth_date}")
    print("="*50)
    
    # Проверяем, существует ли пользователь с таким email
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        print("❌ ОШИБКА: Email уже зарегистрирован!\n")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )
    
    # Хешируем пароль
    hashed_pwd = hash_password(user.password)
    print(f"🔒 Пароль захеширован")
    
    # Создаем нового пользователя
    new_user = User(
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        birth_date=user.birth_date,
        hashed_password=hashed_pwd
    )
    
    # Сохраняем в БД
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print("✅ ПОЛЬЗОВАТЕЛЬ УСПЕШНО СОЗДАН В БД!")
    print(f"🆔 ID пользователя: {new_user.id}")
    
    # Создаем токены для пользователя
    tokens = create_tokens_for_user(new_user, db)
    
    print("🔑 JWT ТОКЕНЫ СОЗДАНЫ")
    print(f"📅 Дата создания: {new_user.created_at}")
    print("="*50 + "\n")
    
    # Возвращаем данные пользователя и токены
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(new_user)
    )

@app.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Вход пользователя в систему
    """
    print("\n" + "="*50)
    print("🔐 ПОПЫТКА ВХОДА:")
    print("="*50)
    print(f"📧 Email: {credentials.email}")
    
    # Ищем пользователя по email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        print("❌ ОШИБКА: Пользователь не найден\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    # Проверяем пароль
    if not verify_password(credentials.password, user.hashed_password):
        print("❌ ОШИБКА: Неверный пароль\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    # Проверяем активность пользователя
    if not user.is_active:
        print("❌ ОШИБКА: Пользователь неактивен\n")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    print("✅ ВХОД УСПЕШЕН!")
    print(f"🆔 ID пользователя: {user.id}")
    
    # Создаем токены для пользователя
    tokens = create_tokens_for_user(user, db)
    
    print("🔑 JWT ТОКЕНЫ СОЗДАНЫ")
    print("="*50 + "\n")
    
    # Возвращаем данные пользователя и токены
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(user)
    )

@app.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Обновление access токена используя refresh токен
    """
    print("\n" + "="*50)
    print("🔄 ОБНОВЛЕНИЕ ACCESS ТОКЕНА")
    print("="*50)
    
    # Ищем все refresh токены в БД (нам нужно сравнить хеши)
    refresh_tokens = db.query(RefreshToken).filter(
        RefreshToken.is_active == True,
        RefreshToken.expires_at > datetime.utcnow()
    ).all()
    
    # Находим токен, который совпадает с предоставленным
    db_refresh_token = None
    for rt in refresh_tokens:
        if verify_token_hash(request.refresh_token, rt.token):
            db_refresh_token = rt
            break
    
    if not db_refresh_token:
        print("❌ ОШИБКА: Невалидный или истекший refresh токен\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истекший refresh токен"
        )
    
    # Получаем пользователя
    user = db.query(User).filter(User.id == db_refresh_token.user_id).first()
    
    if not user or not user.is_active:
        print("❌ ОШИБКА: Пользователь не найден или неактивен\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен"
        )
    
    print(f"✅ REFRESH ТОКЕН ВАЛИДЕН")
    print(f"🆔 ID пользователя: {user.id}")
    
    # Создаем новый access токен
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    )
    
    print("🔑 НОВЫЙ ACCESS ТОКЕН СОЗДАН")
    print("="*50 + "\n")
    
    return AccessTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/logout")
async def logout_user(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Выход пользователя из системы (отзыв refresh токена)
    """
    print("\n" + "="*50)
    print("🚪 ВЫХОД ИЗ СИСТЕМЫ")
    print("="*50)
    
    # Ищем refresh токен в БД
    refresh_tokens = db.query(RefreshToken).filter(
        RefreshToken.is_active == True
    ).all()
    
    # Находим токен, который совпадает с предоставленным
    db_refresh_token = None
    for rt in refresh_tokens:
        if verify_token_hash(request.refresh_token, rt.token):
            db_refresh_token = rt
            break
    
    if db_refresh_token:
        # Отзываем токен
        db_refresh_token.is_active = False
        db.commit()
        print(f"✅ REFRESH ТОКЕН ОТОЗВАН")
        print(f"🆔 ID пользователя: {db_refresh_token.user_id}")
    else:
        print("⚠️ Токен не найден или уже отозван")
    
    print("="*50 + "\n")
    
    return {"message": "Успешный выход из системы"}

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе (требует access токен)
    """
    return UserResponse.model_validate(current_user)

# ===== БИОМЕТРИЯ =====

@app.post("/biometric/register", response_model=BiometricResponse)
async def register_biometric(
    biometric_data: BiometricRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Регистрация биометрических данных пользователя
    """
    print("\n" + "="*50)
    print("🔐 РЕГИСТРАЦИЯ БИОМЕТРИИ:")
    print("="*50)
    print(f"🆔 User ID: {current_user.id}")
    print(f"📧 Email: {current_user.email}")
    print(f"📊 Дескрипторов: {len(biometric_data.descriptor)}")
    print(f"🕐 Timestamp: {biometric_data.timestamp}")
    
    # Проверяем правильность дескриптора (должен быть 128 чисел)
    if len(biometric_data.descriptor) != 128:
        print(f"❌ ОШИБКА: Неверное количество дескрипторов ({len(biometric_data.descriptor)} вместо 128)")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный формат дескрипторов. Ожидается 128 чисел, получено {len(biometric_data.descriptor)}"
        )
    
    # Шифруем дескрипторы с помощью AES-256
    encrypted_descriptors = encrypt_face_descriptor(biometric_data.descriptor)
    
    print(f"🔒 Дескрипторы зашифрованы (AES-256)")
    
    # Проверяем есть ли уже биометрия у пользователя
    existing_biometric = db.query(BiometricData).filter(
        BiometricData.user_id == current_user.id
    ).first()
    
    if existing_biometric:
        # Обновляем существующую биометрию
        print("📝 Обновление существующей биометрии")
        existing_biometric.face_descriptors = encrypted_descriptors
        existing_biometric.updated_at = datetime.utcnow()
        db.commit()
        print("✅ БИОМЕТРИЯ ОБНОВЛЕНА")
    else:
        # Создаем новую запись
        print("➕ Создание новой биометрии")
        new_biometric = BiometricData(
            user_id=current_user.id,
            face_descriptors=encrypted_descriptors
        )
        db.add(new_biometric)
        db.commit()
        print("✅ БИОМЕТРИЯ СОЗДАНА")
    
    # Устанавливаем флаг верификации пользователя
    if not current_user.is_biometric_verified:
        current_user.is_biometric_verified = True
        db.commit()
        db.refresh(current_user)
        print("✅ ПОЛЬЗОВАТЕЛЬ ВЕРИФИЦИРОВАН")
    
    print("="*50 + "\n")
    
    # Обновляем current_user из БД чтобы получить актуальные данные
    db.refresh(current_user)
    
    return BiometricResponse(
        message="Биометрия успешно зарегистрирована",
        user_id=current_user.id,
        verified=True,
        user=UserResponse.model_validate(current_user)
    )

@app.post("/biometric/login", response_model=TokenResponse)
async def login_by_biometric(
    biometric_data: BiometricLogin,
    db: Session = Depends(get_db)
):
    """
    Вход по биометрии (распознавание лица)
    """
    print("\n" + "="*50)
    print("🔐 ВХОД ПО БИОМЕТРИИ:")
    print("="*50)
    print(f"📊 Дескрипторов получено: {len(biometric_data.descriptor)}")
    print(f"🕐 Timestamp: {biometric_data.timestamp}")
    
    # Проверяем правильность дескриптора
    if len(biometric_data.descriptor) != 128:
        print(f"❌ ОШИБКА: Неверное количество дескрипторов ({len(biometric_data.descriptor)} вместо 128)")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный формат дескрипторов. Ожидается 128 чисел, получено {len(biometric_data.descriptor)}"
        )
    
    # Получаем всех пользователей с биометрией
    all_biometric_data = db.query(BiometricData).all()
    
    if not all_biometric_data:
        print("❌ ОШИБКА: Нет пользователей с зарегистрированной биометрией")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Лицо не распознано. Зарегистрируйте биометрию."
        )
    
    print(f"🔍 Проверка среди {len(all_biometric_data)} пользователей...")
    
    # Функция для вычисления евклидова расстояния между дескрипторами
    def euclidean_distance(desc1: list[float], desc2: list[float]) -> float:
        import math
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(desc1, desc2)))
    
    # Порог для сравнения (чем меньше, тем строже)
    MATCH_THRESHOLD = 0.6
    
    best_match_user = None
    best_match_distance = float('inf')
    
    # Сравниваем с каждым пользователем
    for bio_data in all_biometric_data:
        try:
            # Расшифровываем дескрипторы из БД
            stored_descriptor = decrypt_face_descriptor(bio_data.face_descriptors)
            
            # Вычисляем расстояние
            distance = euclidean_distance(biometric_data.descriptor, stored_descriptor)
            
            print(f"  👤 User ID {bio_data.user_id}: расстояние = {distance:.4f}")
            
            # Ищем лучшее совпадение
            if distance < best_match_distance:
                best_match_distance = distance
                best_match_user = bio_data.user_id
                
        except Exception as e:
            print(f"  ⚠️ Ошибка расшифровки для User ID {bio_data.user_id}: {e}")
            continue
    
    # Проверяем порог
    if best_match_distance > MATCH_THRESHOLD:
        print(f"❌ ОШИБКА: Лицо не распознано (лучшее совпадение: {best_match_distance:.4f}, порог: {MATCH_THRESHOLD})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Лицо не распознано. Попробуйте еще раз или войдите с паролем."
        )
    
    # Получаем пользователя
    user = db.query(User).filter(User.id == best_match_user).first()
    
    if not user or not user.is_active:
        print("❌ ОШИБКА: Пользователь не найден или неактивен")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен"
        )
    
    print(f"✅ ЛИЦО РАСПОЗНАНО!")
    print(f"🆔 User ID: {user.id}")
    print(f"📧 Email: {user.email}")
    print(f"📏 Расстояние: {best_match_distance:.4f}")
    
    # Создаем токены для пользователя
    tokens = create_tokens_for_user(user, db)
    
    print("🔑 JWT ТОКЕНЫ СОЗДАНЫ")
    print("="*50 + "\n")
    
    # Возвращаем данные пользователя и токены
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(user)
    )

# ===== SSO ЭНДПОИНТЫ (ЭТАП 1) =====

@app.post("/sso/clients", response_model=OAuthClientCreateResponse)
async def create_oauth_client(
    client_data: OAuthClientCreate,
    current_user: User = Depends(get_current_user),  # Только авторизованные пользователи
    db: Session = Depends(get_db)
):
    """
    Создание нового OAuth клиента (платформы)
    Доступно только для авторизованных пользователей
    """
    print("\n" + "="*50)
    print("🔐 СОЗДАНИЕ OAUTH КЛИЕНТА:")
    print("="*50)
    print(f"📧 Пользователь: {current_user.email}")
    print(f"📛 Название: {client_data.name}")
    print(f"🔗 Redirect URI: {client_data.redirect_uri}")
    
    # Генерируем client_id и client_secret
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    
    # Хешируем client_secret для хранения в БД
    hashed_secret = hash_client_secret(client_secret)
    
    print(f"🆔 Client ID: {client_id}")
    print(f"🔑 Client Secret: {client_secret[:10]}... (полный будет возвращен)")
    
    # Создаем OAuth клиента
    new_client = OAuthClient(
        client_id=client_id,
        client_secret=hashed_secret,
        name=client_data.name,
        redirect_uri=client_data.redirect_uri,
        allowed_scopes=client_data.allowed_scopes,
        is_active=True
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    print("✅ OAUTH КЛИЕНТ УСПЕШНО СОЗДАН!")
    print("="*50 + "\n")
    
    # Возвращаем данные (client_secret показывается только один раз!)
    return OAuthClientCreateResponse(
        client_id=client_id,
        client_secret=client_secret,  # Возвращаем оригинальный secret (только один раз!)
        name=client_data.name,
        redirect_uri=client_data.redirect_uri,
        allowed_scopes=client_data.allowed_scopes,
        message="Клиент успешно создан. Сохраните client_secret, он больше не будет показан!"
    )

@app.get("/sso/clients", response_model=list[OAuthClientResponse])
async def list_oauth_clients(
    current_user: User = Depends(get_current_user),  # Только авторизованные пользователи
    db: Session = Depends(get_db)
):
    """
    Получение списка всех OAuth клиентов (платформ)
    Доступно только для авторизованных пользователей
    """
    print("\n" + "="*50)
    print("📋 СПИСОК OAUTH КЛИЕНТОВ:")
    print("="*50)
    
    clients = db.query(OAuthClient).all()
    
    print(f"🔢 Найдено клиентов: {len(clients)}")
    for client in clients:
        print(f"  - {client.name} (ID: {client.client_id}, Active: {client.is_active})")
    
    print("="*50 + "\n")
    
    # Возвращаем список (БЕЗ client_secret!)
    return [OAuthClientResponse.model_validate(client) for client in clients]

# ===== SSO ЭНДПОИНТЫ (ЭТАП 2: OAuth 2.0 Authorization Code Flow) =====

@app.get("/sso/authorize", response_class=HTMLResponse)
async def authorize_get(
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    state: Optional[str] = None,
    scope: Optional[str] = "openid profile email",
    db: Session = Depends(get_db)
):
    """
    GET /sso/authorize - Показывает форму входа для OAuth 2.0
    
    Платформа перенаправляет пользователя на этот эндпоинт с параметрами:
    - client_id: ID платформы
    - redirect_uri: Куда вернуться после авторизации
    - state: CSRF защита (опционально)
    - scope: Запрашиваемые разрешения
    """
    print("\n" + "="*50)
    print("🔐 OAUTH 2.0 AUTHORIZE REQUEST:")
    print("="*50)
    print(f"🆔 Client ID: {client_id}")
    print(f"🔗 Redirect URI: {redirect_uri}")
    print(f"📋 Response Type: {response_type}")
    print(f"🛡️ State: {state}")
    print(f"📝 Scope: {scope}")
    
    # Проверяем существование клиента
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        print("❌ ОШИБКА: OAuth клиент не найден или неактивен")
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Неверный client_id</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    # Проверяем redirect_uri (должен совпадать с зарегистрированным)
    if client.redirect_uri != redirect_uri:
        print(f"❌ ОШИБКА: Redirect URI не совпадает. Ожидался: {client.redirect_uri}, получен: {redirect_uri}")
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Неверный redirect_uri</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    # Проверяем response_type
    if response_type != "code":
        print(f"❌ ОШИБКА: Неподдерживаемый response_type: {response_type}")
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Поддерживается только response_type=code</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    print("✅ Параметры валидны, показываем форму входа")
    print("="*50 + "\n")
    
    # Возвращаем HTML форму входа
    # В production это должен быть отдельный фронтенд компонент
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Life SSO - Вход</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 400px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                }}
                .platform {{
                    text-align: center;
                    color: #666;
                    margin-bottom: 30px;
                }}
                form {{
                    display: flex;
                    flex-direction: column;
                }}
                input {{
                    padding: 12px;
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                button {{
                    padding: 12px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;
                }}
                button:hover {{
                    background: #0056b3;
                }}
                .error {{
                    color: red;
                    margin-top: 10px;
                    text-align: center;
                }}
                input[type="hidden"] {{
                    display: none;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Life SSO</h1>
                <div class="platform">
                    <p>Вход на платформу: <strong>{client.name}</strong></p>
                </div>
                <form method="POST" action="/sso/authorize">
                    <input type="hidden" name="client_id" value="{client_id}">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="state" value="{state or ''}">
                    <input type="hidden" name="scope" value="{scope}">
                    
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Пароль" required>
                    
                    <button type="submit">Войти</button>
                </form>
            </div>
        </body>
        </html>
        """
    )

@app.post("/sso/authorize")
async def authorize_post(
    request: Request,
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: Optional[str] = Form(None),
    scope: Optional[str] = Form("openid profile email"),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    biometric_descriptor: Optional[str] = Form(None),  # JSON строка с дескриптором
    db: Session = Depends(get_db)
):
    """
    POST /sso/authorize - Обработка входа и создание authorization code
    
    После успешного входа создает authorization code и перенаправляет
    пользователя обратно на платформу с code в параметрах
    """
    ip_address = get_client_ip(request)
    
    print("\n" + "="*50)
    print("🔐 OAUTH 2.0 AUTHORIZE POST:")
    print("="*50)
    print(f"📧 Email: {email or 'биометрия'}")
    print(f"🆔 Client ID: {client_id}")
    print(f"🔗 Redirect URI: {redirect_uri}")
    print(f"🌐 IP: {ip_address}")
    
    # Rate limiting для входа (по IP для биометрии, по email для пароля)
    rate_limit_identifier = email if email else ip_address
    if not check_rate_limit(rate_limit_identifier, max_requests=5, time_window=300):  # 5 попыток в 5 минут
        log_sso_event(
            event_type="authorize_post_rate_limit",
            ip_address=ip_address,
            client_id=client_id,
            success=False,
            details={"email": email, "identifier": rate_limit_identifier}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит попыток входа. Попробуйте через 5 минут."
        )
    
    # Проверяем существование клиента
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        log_sso_event(
            event_type="authorize_post_invalid_client",
            ip_address=ip_address,
            client_id=client_id,
            success=False
        )
        print("❌ ОШИБКА: OAuth клиент не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    # Валидируем redirect_uri
    if not validate_redirect_uri(client.redirect_uri, redirect_uri):
        log_sso_event(
            event_type="authorize_post_invalid_redirect_uri",
            ip_address=ip_address,
            client_id=client_id,
            success=False,
            details={"provided_uri": redirect_uri}
        )
        print(f"❌ ОШИБКА: Неверный redirect_uri")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный redirect_uri"
        )
    
    # Валидируем scope
    if not validate_scope(scope or "", client.allowed_scopes):
        log_sso_event(
            event_type="authorize_post_invalid_scope",
            ip_address=ip_address,
            client_id=client_id,
            success=False,
            details={"requested_scope": scope}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Запрошенный scope не разрешен"
        )
    
    # Проверяем учетные данные пользователя
    user = None
    
    # Если передан биометрический дескриптор - проверяем биометрию
    if biometric_descriptor:
        print("🔐 Проверка биометрии...")
        try:
            import json
            biometric_data = json.loads(biometric_descriptor)
            descriptor = biometric_data.get('descriptor')
            
            if not descriptor or len(descriptor) != 128:
                print(f"❌ ОШИБКА: Неверный формат дескриптора")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный формат биометрического дескриптора"
                )
            
            # Получаем всех пользователей с биометрией
            all_biometric_data = db.query(BiometricData).all()
            
            if not all_biometric_data:
                print("❌ ОШИБКА: Нет пользователей с зарегистрированной биометрией")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Лицо не распознано. Зарегистрируйте биометрию."
                )
            
            # Функция для вычисления евклидова расстояния
            def euclidean_distance(desc1: list[float], desc2: list[float]) -> float:
                import math
                return math.sqrt(sum((a - b) ** 2 for a, b in zip(desc1, desc2)))
            
            MATCH_THRESHOLD = 0.6
            best_match_user_id = None
            best_match_distance = float('inf')
            
            # Сравниваем с каждым пользователем
            for bio_data in all_biometric_data:
                try:
                    stored_descriptor = decrypt_face_descriptor(bio_data.face_descriptors)
                    distance = euclidean_distance(descriptor, stored_descriptor)
                    
                    if distance < best_match_distance:
                        best_match_distance = distance
                        best_match_user_id = bio_data.user_id
                except Exception as e:
                    print(f"  ⚠️ Ошибка расшифровки для User ID {bio_data.user_id}: {e}")
                    continue
            
            # Проверяем порог
            if best_match_distance > MATCH_THRESHOLD:
                print(f"❌ ОШИБКА: Лицо не распознано (расстояние: {best_match_distance:.4f})")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Лицо не распознано. Попробуйте еще раз или войдите с паролем."
                )
            
            # Получаем пользователя
            user = db.query(User).filter(User.id == best_match_user_id).first()
            
            if not user:
                print("❌ ОШИБКА: Пользователь не найден")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Пользователь не найден"
                )
            
            print(f"✅ Лицо распознано! User ID: {user.id}, расстояние: {best_match_distance:.4f}")
            
        except json.JSONDecodeError:
            print("❌ ОШИБКА: Неверный JSON формат биометрического дескриптора")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат биометрических данных"
            )
    
    # Если передан password - проверяем пароль
    elif password and email:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print("❌ ОШИБКА: Пользователь не найден")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        if not verify_password(password, user.hashed_password):
            print("❌ ОШИБКА: Неверный пароль")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        print(f"✅ Вход по паролю успешен! User ID: {user.id}")
    else:
        # Ни пароль, ни биометрия не переданы
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать либо пароль (email+password), либо биометрический дескриптор"
        )
    
    if not user.is_active:
        print("❌ ОШИБКА: Пользователь неактивен")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    print(f"✅ Вход успешен! User ID: {user.id}")
    
    # Логируем успешный вход
    log_sso_event(
        event_type="authorize_post_success",
        user_id=user.id,
        client_id=client_id,
        ip_address=ip_address,
        success=True,
        details={"email": email}
    )
    
    # Генерируем authorization code
    auth_code = generate_authorization_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # Code живет 10 минут
    
    # Сохраняем code в БД
    authorization_code = OAuthAuthorizationCode(
        code=auth_code,
        client_id=client_id,
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scope,
        expires_at=expires_at,
        is_used=False
    )
    
    db.add(authorization_code)
    db.commit()
    
    print(f"🔑 Authorization code создан: {auth_code[:10]}...")
    print(f"⏰ Истекает через: {expires_at}")
    
    # Формируем URL для редиректа
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"
    
    print(f"🔗 Редирект на: {redirect_url}")
    print("="*50 + "\n")
    
    # Перенаправляем пользователя обратно на платформу с code
    return RedirectResponse(url=redirect_url, status_code=302)

@app.post("/sso/token", response_model=OAuthTokenResponse)
async def token(
    http_request: Request,
    grant_type: str = Form("authorization_code"),
    code: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    POST /sso/token - Обмен authorization code на токены
    
    Платформа отправляет authorization code и получает access/refresh токены
    Принимает application/x-www-form-urlencoded данные (OAuth 2.0 стандарт)
    """
    ip_address = get_client_ip(http_request)
    
    print("\n" + "="*50)
    print("🔄 OAUTH 2.0 TOKEN EXCHANGE:")
    print("="*50)
    print(f"📝 Grant Type: {grant_type}")
    print(f"🔑 Code: {code[:10]}...")
    print(f"🌐 IP: {ip_address}")
    
    # Rate limiting для token exchange (по client_id)
    if not check_rate_limit(client_id, max_requests=10, time_window=60):
        log_sso_event(
            event_type="token_exchange_rate_limit",
            ip_address=ip_address,
            client_id=client_id,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит запросов токенов. Попробуйте через минуту."
        )
    print(f"🆔 Client ID: {client_id}")
    print(f"🔗 Redirect URI: {redirect_uri}")
    
    # Проверяем grant_type
    if grant_type != "authorization_code":
        print(f"❌ ОШИБКА: Неподдерживаемый grant_type: {grant_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживается только grant_type=authorization_code"
        )
    
    # Находим authorization code в БД
    auth_code = db.query(OAuthAuthorizationCode).filter(
        OAuthAuthorizationCode.code == code,
        OAuthAuthorizationCode.is_used == False
    ).first()
    
    if not auth_code:
        print("❌ ОШИБКА: Authorization code не найден или уже использован")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истекший authorization code"
        )
    
    # Проверяем срок действия code
    if auth_code.expires_at < datetime.utcnow():
        print("❌ ОШИБКА: Authorization code истек")
        # Помечаем как использованный
        auth_code.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code истек"
        )
    
    # Проверяем client_id
    if auth_code.client_id != client_id:
        print(f"❌ ОШИБКА: Client ID не совпадает")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    # Проверяем redirect_uri
    if auth_code.redirect_uri != redirect_uri:
        print(f"❌ ОШИБКА: Redirect URI не совпадает")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный redirect_uri"
        )
    
    # Проверяем client_secret
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        print("❌ ОШИБКА: OAuth клиент не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    if not verify_client_secret(client_secret, client.client_secret):
        print("❌ ОШИБКА: Неверный client_secret")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный client_secret"
        )
    
    print("✅ Все проверки пройдены")
    
    # Получаем пользователя
    user = db.query(User).filter(User.id == auth_code.user_id).first()
    
    if not user or not user.is_active:
        print("❌ ОШИБКА: Пользователь не найден или неактивен")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен"
        )
    
    # Помечаем code как использованный (одноразовый!)
    auth_code.is_used = True
    db.commit()
    
    print(f"✅ Authorization code помечен как использованный")
    print(f"👤 User ID: {user.id}")
    print(f"📧 Email: {user.email}")
    
    # Создаем токены для пользователя
    tokens = create_tokens_for_user(user, db)
    
    print("🔑 JWT ТОКЕНЫ СОЗДАНЫ")
    print("="*50 + "\n")
    
    # Логируем успешный обмен токенов
    log_sso_event(
        event_type="token_exchange_success",
        user_id=user.id,
        client_id=client_id,
        ip_address=ip_address,
        success=True
    )
    
    # Возвращаем токены и данные пользователя
    return OAuthTokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(user)
    )

# ===== SSO ЭНДПОИНТЫ (ЭТАП 3: QR Code Flow) =====

@app.post("/sso/qr/initiate", response_model=QRInitiateResponse)
async def qr_initiate(
    http_request: Request,
    request: QRInitiateRequest,
    db: Session = Depends(get_db)
):
    """
    POST /sso/qr/initiate - Создание QR сессии для OAuth Device Flow
    
    Платформа запрашивает создание QR-кода для входа.
    Возвращает device_code, user_code и URL для сканирования.
    """
    ip_address = get_client_ip(http_request)
    
    print("\n" + "="*50)
    print("📱 QR CODE FLOW INITIATE:")
    print("="*50)
    print(f"🆔 Client ID: {request.client_id}")
    print(f"📝 Scope: {request.scope}")
    print(f"🌐 IP: {ip_address}")
    
    # Rate limiting по client_id
    if not check_rate_limit(request.client_id, max_requests=10, time_window=60):
        log_sso_event(
            event_type="qr_initiate_rate_limit",
            ip_address=ip_address,
            client_id=request.client_id,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит запросов QR сессий"
        )
    
    # Проверяем существование клиента
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == request.client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        log_sso_event(
            event_type="qr_initiate_invalid_client",
            ip_address=ip_address,
            client_id=request.client_id,
            success=False
        )
        print("❌ ОШИБКА: OAuth клиент не найден или неактивен")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    # Валидируем scope
    if not validate_scope(request.scope or "", client.allowed_scopes):
        log_sso_event(
            event_type="qr_initiate_invalid_scope",
            ip_address=ip_address,
            client_id=request.client_id,
            success=False,
            details={"requested_scope": request.scope}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Запрошенный scope не разрешен"
        )
    
    # Генерируем device_code и user_code
    device_code = generate_device_code()
    user_code = generate_user_code()
    
    # Время жизни QR-кода (10 минут)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Создаем запись в БД
    device_code_record = OAuthDeviceCode(
        device_code=device_code,
        user_code=user_code,
        client_id=request.client_id,
        user_id=None,  # Пока не авторизован
        scope=request.scope,
        status='pending',  # pending → authorized → expired
        expires_at=expires_at
    )
    
    db.add(device_code_record)
    db.commit()
    
    # Формируем URL для верификации (фронтенд Life SSO)
    # В продакшене здесь должен быть реальный домен
    verification_uri = "http://localhost:3000/sso/qr/verify"
    verification_uri_complete = f"{verification_uri}?user_code={user_code}"
    
    print(f"✅ QR сессия создана!")
    print(f"   Device Code: {device_code[:20]}...")
    print(f"   User Code: {user_code}")
    print(f"   Expires At: {expires_at}")
    print("="*50 + "\n")
    
    return QRInitiateResponse(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        verification_uri_complete=verification_uri_complete,
        expires_in=600,  # 10 минут в секундах
        interval=5  # Интервал для polling
    )

@app.get("/sso/qr/verify", response_class=HTMLResponse)
async def qr_verify_get(
    user_code: str,
    db: Session = Depends(get_db)
):
    """
    GET /sso/qr/verify - Страница для входа по QR-коду
    
    Пользователь сканирует QR и попадает на эту страницу с user_code.
    Показывается форма входа.
    """
    print("\n" + "="*50)
    print("📱 QR VERIFY GET:")
    print("="*50)
    print(f"🔑 User Code: {user_code}")
    
    # Ищем device_code по user_code
    device_code_record = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.user_code == user_code,
        OAuthDeviceCode.status == 'pending'
    ).first()
    
    if not device_code_record:
        print("❌ ОШИБКА: User code не найден или уже использован")
        return HTMLResponse(
            content="""
            <html>
                <body>
                    <h1>Ошибка</h1>
                    <p>QR-код недействителен или истек</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    # Проверяем срок действия
    if device_code_record.expires_at < datetime.utcnow():
        print("❌ ОШИБКА: QR-код истек")
        device_code_record.status = 'expired'
        db.commit()
        return HTMLResponse(
            content="""
            <html>
                <body>
                    <h1>Ошибка</h1>
                    <p>QR-код истек. Пожалуйста, отсканируйте новый QR-код.</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    print("✅ User code валиден, показываем форму входа")
    print("="*50 + "\n")
    
    # Получаем информацию о платформе
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == device_code_record.client_id
    ).first()
    
    platform_name = client.name if client else "платформу"
    
    # Возвращаем HTML форму входа
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Life SSO - Вход по QR</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 400px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                }}
                .code-display {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 4px;
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 24px;
                    font-weight: bold;
                    color: #007bff;
                    letter-spacing: 2px;
                }}
                .platform {{
                    text-align: center;
                    color: #666;
                    margin-bottom: 30px;
                }}
                form {{
                    display: flex;
                    flex-direction: column;
                }}
                input {{
                    padding: 12px;
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                button {{
                    padding: 12px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;
                }}
                button:hover {{
                    background: #0056b3;
                }}
                .error {{
                    color: red;
                    margin-top: 10px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Life SSO</h1>
                <div class="platform">
                    <p>Вход на платформу: <strong>{platform_name}</strong></p>
                </div>
                <div class="code-display">
                    {user_code}
                </div>
                <form method="POST" action="/sso/qr/verify">
                    <input type="hidden" name="user_code" value="{user_code}">
                    
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Пароль" required>
                    
                    <button type="submit">Войти</button>
                </form>
            </div>
        </body>
        </html>
        """
    )

@app.post("/sso/qr/verify")
async def qr_verify_post(
    user_code: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    POST /sso/qr/verify - Обработка входа по QR-коду
    
    После успешного входа связывает device_code с пользователем
    и меняет статус на 'authorized'
    """
    print("\n" + "="*50)
    print("📱 QR VERIFY POST:")
    print("="*50)
    print(f"🔑 User Code: {user_code}")
    print(f"📧 Email: {email}")
    
    # Находим device_code по user_code
    device_code_record = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.user_code == user_code,
        OAuthDeviceCode.status == 'pending'
    ).first()
    
    if not device_code_record:
        print("❌ ОШИБКА: User code не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истекший user_code"
        )
    
    # Проверяем срок действия
    if device_code_record.expires_at < datetime.utcnow():
        print("❌ ОШИБКА: QR-код истек")
        device_code_record.status = 'expired'
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR-код истек"
        )
    
    # Проверяем учетные данные пользователя
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        print("❌ ОШИБКА: Пользователь не найден")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not verify_password(password, user.hashed_password):
        print("❌ ОШИБКА: Неверный пароль")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not user.is_active:
        print("❌ ОШИБКА: Пользователь неактивен")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    print(f"✅ Вход успешен! User ID: {user.id}")
    
    # Связываем device_code с пользователем
    device_code_record.user_id = user.id
    device_code_record.status = 'authorized'
    db.commit()
    
    print(f"✅ Device code авторизован!")
    print(f"   Device Code: {device_code_record.device_code[:20]}...")
    print(f"   User ID: {user.id}")
    print("="*50 + "\n")
    
    # Возвращаем страницу успеха
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Авторизация успешна</title>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 400px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }
                .success {
                    color: #28a745;
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                p {
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>Авторизация успешна!</h1>
                <p>Вы можете закрыть эту страницу.</p>
                <p>Платформа получит уведомление о вашем входе.</p>
            </div>
        </body>
        </html>
        """
    )

@app.post("/sso/qr/token", response_model=QRTokenResponse)
async def qr_token(
    request: QRTokenRequest,
    db: Session = Depends(get_db)
):
    """
    POST /sso/qr/token - Проверка статуса QR и получение токенов
    
    Платформа опрашивает этот эндпоинт (polling) каждые 5 секунд
    пока статус не станет 'authorized', затем получает токены
    """
    print("\n" + "="*50)
    print("📱 QR TOKEN REQUEST:")
    print("="*50)
    print(f"🔑 Device Code: {request.device_code[:20]}...")
    print(f"🆔 Client ID: {request.client_id}")
    
    # Проверяем client_secret
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == request.client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        print("❌ ОШИБКА: OAuth клиент не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    if not verify_client_secret(request.client_secret, client.client_secret):
        print("❌ ОШИБКА: Неверный client_secret")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный client_secret"
        )
    
    # Находим device_code в БД
    device_code_record = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.device_code == request.device_code,
        OAuthDeviceCode.client_id == request.client_id
    ).first()
    
    if not device_code_record:
        print("❌ ОШИБКА: Device code не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный device_code"
        )
    
    # Проверяем срок действия
    if device_code_record.expires_at < datetime.utcnow():
        print("❌ ОШИБКА: QR-код истек")
        if device_code_record.status == 'pending':
            device_code_record.status = 'expired'
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR-код истек"
        )
    
    # Если статус pending - возвращаем ожидание
    if device_code_record.status == 'pending':
        print("⏳ Статус: pending (ожидание авторизации)")
        print("="*50 + "\n")
        return QRTokenResponse(
            status="pending",
            message="Ожидание авторизации... Пожалуйста, отсканируйте QR-код и войдите."
        )
    
    # Если статус expired - ошибка
    if device_code_record.status == 'expired':
        print("❌ ОШИБКА: Статус expired")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR-код истек"
        )
    
    # Если статус authorized - возвращаем токены
    if device_code_record.status == 'authorized':
        print("✅ Статус: authorized")
        
        # Получаем пользователя
        user = db.query(User).filter(User.id == device_code_record.user_id).first()
        
        if not user or not user.is_active:
            print("❌ ОШИБКА: Пользователь не найден или неактивен")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или неактивен"
            )
        
        print(f"👤 User ID: {user.id}")
        print(f"📧 Email: {user.email}")
        
        # Создаем токены для пользователя
        tokens = create_tokens_for_user(user, db)
        
        # Помечаем device_code как использованный (можно удалить или оставить для истории)
        # Для QR flow обычно не помечаем как использованный, т.к. это не одноразовый код как authorization code
        
        print("🔑 JWT ТОКЕНЫ СОЗДАНЫ")
        print("="*50 + "\n")
        
        return QRTokenResponse(
            status="authorized",
            message="Авторизация успешна!",
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=tokens["expires_in"],
            user=UserResponse.model_validate(user)
        )
    
    # Неожиданный статус
    print(f"⚠️  Неожиданный статус: {device_code_record.status}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Неожиданный статус device_code"
    )

# ===== SSO ЭНДПОИНТЫ (ЭТАП 4: Code Flow / Magic Link / OTP) =====

@app.post("/sso/code/request", response_model=CodeRequestResponse)
async def code_request(
    http_request: Request,
    request: CodeRequestRequest,
    db: Session = Depends(get_db)
):
    """
    POST /sso/code/request - Запрос 6-цифрового кода для входа
    
    Пользователь вводит email или имя на платформе.
    SSO генерирует код и сохраняет его - код показывается на Life SSO.
    """
    ip_address = get_client_ip(http_request)
    
    print("\n" + "="*50)
    print("🔢 CODE REQUEST:")
    print("="*50)
    print(f"🆔 Client ID: {request.client_id}")
    print(f"📧 Identifier: {request.identifier}")
    print(f"🌐 IP: {ip_address}")
    
    # Rate limiting - 1 запрос кода в минуту на identifier
    if not check_rate_limit(request.identifier, max_requests=1, time_window=60):
        log_sso_event(
            event_type="code_request_rate_limit",
            ip_address=ip_address,
            client_id=request.client_id,
            success=False,
            details={"identifier": request.identifier}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Код уже был запрошен. Подождите 1 минуту перед повторным запросом."
        )
    
    # Проверяем существование клиента
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == request.client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        log_sso_event(
            event_type="code_request_invalid_client",
            ip_address=ip_address,
            client_id=request.client_id,
            success=False
        )
        print("❌ ОШИБКА: OAuth клиент не найден или неактивен")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    # Ищем пользователя по email или имени
    # Сначала пробуем email
    user = db.query(User).filter(User.email == request.identifier).first()
    
    # Если не найден по email, пробуем по имени
    if not user:
        user = db.query(User).filter(User.full_name == request.identifier).first()
    
    if not user:
        print("❌ ОШИБКА: Пользователь не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Убедитесь, что вы указали правильный email или имя."
        )
    
    if not user.is_active:
        print("❌ ОШИБКА: Пользователь неактивен")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    print(f"✅ Пользователь найден: {user.email}")
    
    # Генерируем код и code_id
    code = generate_verification_code()
    code_id = generate_code_id()
    
    # Время жизни кода (5 минут)
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Сохраняем код в БД
    verification_code_record = OAuthVerificationCode(
        code_id=code_id,
        code=code,
        client_id=request.client_id,
        user_id=user.id,
        redirect_uri=request.redirect_uri,
        attempts=0,
        max_attempts=5,
        is_used=False,
        expires_at=expires_at
    )
    
    db.add(verification_code_record)
    db.commit()
    
    print(f"✅ Код создан!")
    print(f"   Code ID: {code_id[:20]}...")
    print(f"   Code: {code}")
    print(f"   User ID: {user.id}")
    print(f"   Expires At: {expires_at}")
    
    # TODO: Отправить код по email/SMS (пока заглушка)
    # send_code_to_user(user.email, code)
    
    print("="*50 + "\n")
    
    # Логируем создание кода
    log_sso_event(
        event_type="code_request_success",
        user_id=user.id,
        client_id=request.client_id,
        ip_address=ip_address,
        success=True,
        details={"identifier": request.identifier}
    )
    
    # Код создан и сохранен в БД, пользователь увидит его на странице /sso/codes
    # Платформе не возвращаем код напрямую - он будет на Life SSO
    return CodeRequestResponse(
        code_id=code_id,
        code=None,  # НЕ возвращаем код платформе - он показывается на Life SSO
        message=f"Код отправлен. Откройте Life SSO и перейдите в раздел 'Коды для входа на платформы' чтобы увидеть ваш код.",
        expires_in=300  # 5 минут в секундах
    )

@app.post("/sso/code/verify", response_model=CodeVerifyResponse)
async def code_verify(
    http_request: Request,
    request: CodeVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    POST /sso/code/verify - Проверка 6-цифрового кода и получение токенов
    
    Платформа проверяет введенный пользователем код.
    Если код верный и не истек - возвращаются токены.
    """
    ip_address = get_client_ip(http_request)
    
    print("\n" + "="*50)
    print("🔢 CODE VERIFY:")
    print("="*50)
    print(f"🆔 Client ID: {request.client_id}")
    print(f"🔑 Code ID: {request.code_id[:20]}...")
    print(f"🔢 Code: {request.code}")
    print(f"🌐 IP: {ip_address}")
    
    # Rate limiting по client_id
    if not check_rate_limit(request.client_id, max_requests=20, time_window=60):
        log_sso_event(
            event_type="code_verify_rate_limit",
            ip_address=ip_address,
            client_id=request.client_id,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит попыток проверки кода"
        )
    
    # Проверяем client_secret
    client = db.query(OAuthClient).filter(
        OAuthClient.client_id == request.client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        print("❌ ОШИБКА: OAuth клиент не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный client_id"
        )
    
    if not verify_client_secret(request.client_secret, client.client_secret):
        print("❌ ОШИБКА: Неверный client_secret")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный client_secret"
        )
    
    # Находим код в БД
    verification_code_record = db.query(OAuthVerificationCode).filter(
        OAuthVerificationCode.code_id == request.code_id,
        OAuthVerificationCode.client_id == request.client_id
    ).first()
    
    if not verification_code_record:
        print("❌ ОШИБКА: Code ID не найден")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный code_id"
        )
    
    # Проверяем срок действия
    if verification_code_record.expires_at < datetime.utcnow():
        print("❌ ОШИБКА: Код истек")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код истек. Запросите новый код."
        )
    
    # Проверяем, не использован ли код
    if verification_code_record.is_used:
        print("❌ ОШИБКА: Код уже использован")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код уже использован. Запросите новый код."
        )
    
    # Проверяем количество попыток
    verification_code_record.attempts += 1
    if verification_code_record.attempts > verification_code_record.max_attempts:
        print("❌ ОШИБКА: Превышено количество попыток")
        verification_code_record.is_used = True  # Блокируем код
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Превышено максимальное количество попыток ({verification_code_record.max_attempts}). Запросите новый код."
        )
    
    # Проверяем сам код
    if verification_code_record.code != request.code:
        print(f"❌ ОШИБКА: Неверный код. Попытка {verification_code_record.attempts}/{verification_code_record.max_attempts}")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный код. Осталось попыток: {verification_code_record.max_attempts - verification_code_record.attempts}"
        )
    
    # Код верный! Получаем пользователя
    user = db.query(User).filter(User.id == verification_code_record.user_id).first()
    
    # Проверка на фиктивный код (user_id = -1 означает, что пользователь не найден при запросе)
    # Также проверяем, что пользователь существует и активен
    if not user or verification_code_record.user_id == -1 or not user.is_active:
        print("❌ ОШИБКА: Пользователь не найден или неактивен")
        verification_code_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен"
        )
    
    print(f"✅ Код верный!")
    print(f"   User ID: {user.id}")
    print(f"   Email: {user.email}")
    
    # Помечаем код как использованный
    verification_code_record.is_used = True
    db.commit()
    
    # Создаем токены для пользователя
    tokens = create_tokens_for_user(user, db)
    
    print("🔑 JWT ТОКЕНЫ СОЗДАНЫ")
    print("="*50 + "\n")
    
    return CodeVerifyResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        user=UserResponse.model_validate(user)
    )

@app.get("/sso/codes/my")
async def get_my_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GET /sso/codes/my - Получить активные коды пользователя для отображения на странице уведомлений
    
    Возвращает:
    - Активные verification codes (для Code flow)
    - Активные device codes с pending статусом (для QR flow)
    """
    print("\n" + "="*50)
    print("📋 GET MY CODES:")
    print("="*50)
    print(f"👤 User ID: {current_user.id}")
    print(f"📧 Email: {current_user.email}")
    
    codes = []
    
    # 1. Получаем активные verification codes (Code flow)
    verification_codes = db.query(OAuthVerificationCode).filter(
        OAuthVerificationCode.user_id == current_user.id,
        OAuthVerificationCode.is_used == False,
        OAuthVerificationCode.expires_at > datetime.utcnow()
    ).all()
    
    for vc in verification_codes:
        client = db.query(OAuthClient).filter(OAuthClient.client_id == vc.client_id).first()
        codes.append({
            "code_id": vc.code_id,
            "code": vc.code,
            "type": "code",
            "platform_name": client.name if client else "Неизвестная платформа",
            "created_at": vc.created_at.isoformat(),
            "expires_at": vc.expires_at.isoformat(),
        })
    
    # 2. Получаем активные device codes с pending статусом (QR flow)
    # Показываем только те, где пользователь уже авторизовался (user_id установлен)
    # Это значит, что пользователь отсканировал QR и вошел, но еще не завершил авторизацию
    device_codes = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.user_id == current_user.id,
        OAuthDeviceCode.status == 'pending',
        OAuthDeviceCode.expires_at > datetime.utcnow()
    ).all()
    
    # Также показываем authorized QR коды (еще не получены токены платформой)
    device_codes_authorized = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.user_id == current_user.id,
        OAuthDeviceCode.status == 'authorized',
        OAuthDeviceCode.expires_at > datetime.utcnow()
    ).all()
    
    device_codes.extend(device_codes_authorized)
    
    for dc in device_codes:
        client = db.query(OAuthClient).filter(OAuthClient.client_id == dc.client_id).first()
        verification_uri = "http://localhost:3000/sso/qr/verify"
        verification_uri_complete = f"{verification_uri}?user_code={dc.user_code}"
        codes.append({
            "code_id": dc.device_code,
            "user_code": dc.user_code,
            "type": "qr",
            "platform_name": client.name if client else "Неизвестная платформа",
            "verification_uri": verification_uri,
            "verification_uri_complete": verification_uri_complete,
            "created_at": dc.created_at.isoformat(),
            "expires_at": dc.expires_at.isoformat(),
        })
    
    print(f"✅ Найдено активных кодов: {len(codes)}")
    print("="*50 + "\n")
    
    return {"codes": codes}