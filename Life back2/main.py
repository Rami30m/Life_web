from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from schemas import (
    UserCreate, UserResponse, UserLogin, 
    TokenResponse, RefreshTokenRequest, AccessTokenResponse,
    BiometricRegister, BiometricResponse, BiometricLogin
)
from models import User, RefreshToken, BiometricData
from database import get_db
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    hash_token, verify_token_hash,
    decode_access_token, get_user_from_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    encrypt_face_descriptor, decrypt_face_descriptor
)

# Таблицы создаются через Alembic миграции
app = FastAPI(title="Life SSO API", version="1.0.0")

# Настройка CORS для связи с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
