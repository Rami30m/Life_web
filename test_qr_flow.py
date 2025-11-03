"""
Тестовый скрипт для проверки QR Code Flow (Этап 3 SSO)

Этот скрипт автоматизирует тестирование входа по QR-коду:
1. Регистрация/вход пользователя
2. Создание OAuth клиента
3. Инициация QR сессии
4. Имитация сканирования QR (открытие браузера)
5. Polling статуса до получения токенов
"""

import requests
import time
import webbrowser
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"

def register_user(email: str, password: str, full_name: str = "Test User") -> Dict:
    """Регистрация нового пользователя"""
    print(f"\n📝 Регистрация пользователя: {email}")
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name
        }
    )
    if response.status_code == 200:
        print("✅ Пользователь зарегистрирован")
        return response.json()
    elif response.status_code == 400 and "уже существует" in response.json().get("detail", ""):
        print("⚠️  Пользователь уже существует, выполняем вход...")
        return login_user(email, password)
    else:
        print(f"❌ Ошибка регистрации: {response.json()}")
        raise Exception(f"Ошибка регистрации: {response.status_code}")

def login_user(email: str, password: str) -> Dict:
    """Вход пользователя"""
    print(f"\n🔐 Вход пользователя: {email}")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": email,
            "password": password
        }
    )
    if response.status_code == 200:
        print("✅ Вход успешен")
        return response.json()
    else:
        print(f"❌ Ошибка входа: {response.json()}")
        raise Exception(f"Ошибка входа: {response.status_code}")

def create_oauth_client(token: str, name: str = "QR Test Platform", redirect_uri: str = "http://localhost:3001/callback") -> Dict:
    """Создание OAuth клиента"""
    print(f"\n🆔 Создание OAuth клиента: {name}")
    response = requests.post(
        f"{BASE_URL}/sso/clients",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "redirect_uri": redirect_uri,
            "allowed_scopes": "openid profile email"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ OAuth клиент создан")
        print(f"   Client ID: {data['client_id'][:20]}...")
        print(f"   Client Secret: {data['client_secret'][:20]}...")
        return data
    else:
        print(f"❌ Ошибка создания клиента: {response.json()}")
        raise Exception(f"Ошибка создания клиента: {response.status_code}")

def initiate_qr_session(client_id: str) -> Dict:
    """Инициация QR сессии"""
    print(f"\n📱 Инициация QR сессии...")
    response = requests.post(
        f"{BASE_URL}/sso/qr/initiate",
        json={
            "client_id": client_id,
            "scope": "openid profile email"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print("✅ QR сессия создана")
        print(f"   Device Code: {data['device_code'][:20]}...")
        print(f"   User Code: {data['user_code']}")
        print(f"   Verification URI: {data['verification_uri_complete']}")
        print(f"   Expires In: {data['expires_in']} секунд")
        return data
    else:
        print(f"❌ Ошибка инициации QR: {response.json()}")
        raise Exception(f"Ошибка инициации QR: {response.status_code}")

def poll_qr_status(device_code: str, client_id: str, client_secret: str, max_attempts: int = 120) -> Optional[Dict]:
    """
    Polling статуса QR до получения токенов
    
    Args:
        device_code: Device code для проверки
        client_id: Client ID
        client_secret: Client Secret
        max_attempts: Максимальное количество попыток (по умолчанию 120 = 10 минут при интервале 5 сек)
    
    Returns:
        Dict с токенами или None если истекло время
    """
    print(f"\n🔄 Начинаем polling статуса QR...")
    print(f"   Максимум попыток: {max_attempts}")
    print(f"   Интервал: 5 секунд")
    print(f"   (Ожидаем, пока пользователь не отсканирует QR и не войдет)")
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n   Попытка {attempt}/{max_attempts}...")
        
        response = requests.post(
            f"{BASE_URL}/sso/qr/token",
            json={
                "device_code": device_code,
                "client_id": client_id,
                "client_secret": client_secret
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data["status"] == "pending":
                print(f"   ⏳ Статус: pending - ожидание авторизации...")
                if attempt < max_attempts:
                    print(f"   ⏸️  Ждем 5 секунд перед следующей попыткой...")
                    time.sleep(5)
                else:
                    print("❌ Превышено максимальное количество попыток")
                    return None
                    
            elif data["status"] == "authorized":
                print("✅ Статус: authorized - токены получены!")
                print(f"   Access Token: {data['access_token'][:30]}...")
                print(f"   Refresh Token: {data['refresh_token'][:30]}...")
                print(f"   User: {data['user']['email']}")
                return data
            else:
                print(f"⚠️  Неожиданный статус: {data.get('status')}")
                return data
        else:
            error_data = response.json()
            print(f"❌ Ошибка polling: {error_data}")
            
            if "истек" in error_data.get("detail", "").lower():
                print("   QR-код истек, завершаем polling")
                return None
            else:
                # Для других ошибок продолжаем попытки
                if attempt < max_attempts:
                    time.sleep(5)
                else:
                    return None
    
    print("❌ Превышено максимальное время ожидания")
    return None

def main():
    """Основная функция тестирования QR flow"""
    print("="*60)
    print("🧪 ТЕСТИРОВАНИЕ QR CODE FLOW (ЭТАП 3 SSO)")
    print("="*60)
    
    try:
        # 1. Регистрация/вход пользователя
        user_email = "qr_test@example.com"
        user_password = "test_password_123"
        
        try:
            user_data = register_user(user_email, user_password)
        except:
            user_data = login_user(user_email, user_password)
        
        access_token = user_data["access_token"]
        print(f"\n✅ Токен пользователя получен: {access_token[:30]}...")
        
        # 2. Создание OAuth клиента
        client_data = create_oauth_client(access_token)
        client_id = client_data["client_id"]
        client_secret = client_data["client_secret"]
        
        # 3. Инициация QR сессии
        qr_data = initiate_qr_session(client_id)
        device_code = qr_data["device_code"]
        user_code = qr_data["user_code"]
        verification_uri_complete = qr_data["verification_uri_complete"]
        
        # 4. Открываем браузер для сканирования QR
        print(f"\n🌐 Открываем страницу верификации в браузере...")
        print(f"   URL: {verification_uri_complete}")
        print(f"\n📋 ИНСТРУКЦИЯ:")
        print(f"   1. В открывшемся браузере вы увидите форму входа")
        print(f"   2. User Code должен быть: {user_code}")
        print(f"   3. Введите email: {user_email}")
        print(f"   4. Введите пароль: {user_password}")
        print(f"   5. Нажмите 'Войти'")
        print(f"   6. После успешного входа эта страница закроется")
        print(f"\n   ⚠️  Скрипт продолжит polling после открытия браузера")
        print(f"      НЕ закрывайте этот терминал!")
        
        # Небольшая задержка перед открытием браузера
        time.sleep(2)
        
        # Открываем браузер
        webbrowser.open(verification_uri_complete)
        
        # 5. Polling статуса до получения токенов
        print(f"\n⏳ Начинаем polling через 3 секунды...")
        time.sleep(3)
        
        tokens = poll_qr_status(device_code, client_id, client_secret, max_attempts=120)
        
        if tokens:
            print("\n" + "="*60)
            print("✅ QR FLOW УСПЕШНО ЗАВЕРШЕН!")
            print("="*60)
            print(f"📧 Пользователь: {tokens['user']['email']}")
            print(f"🔑 Access Token: {tokens['access_token'][:50]}...")
            print(f"🔄 Refresh Token: {tokens['refresh_token'][:50]}...")
            print(f"⏰ Expires In: {tokens['expires_in']} секунд")
        else:
            print("\n" + "="*60)
            print("❌ QR FLOW НЕ ЗАВЕРШЕН")
            print("="*60)
            print("Возможные причины:")
            print("   - Пользователь не завершил вход")
            print("   - QR-код истек (10 минут)")
            print("   - Превышено время ожидания")
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

