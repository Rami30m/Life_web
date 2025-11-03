"""
Тестовый скрипт для проверки Code Flow (Этап 4 SSO)

Этот скрипт автоматизирует тестирование входа по 6-цифровому коду:
1. Регистрация/вход пользователя
2. Создание OAuth клиента
3. Запрос кода по email/имени
4. Получение и отображение кода
5. Проверка кода и получение токенов
"""

import requests
from typing import Dict

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

def create_oauth_client(token: str, name: str = "Code Test Platform", redirect_uri: str = "http://localhost:3001/callback") -> Dict:
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

def request_code(client_id: str, identifier: str) -> Dict:
    """Запрос 6-цифрового кода"""
    print(f"\n🔢 Запрос кода для: {identifier}")
    response = requests.post(
        f"{BASE_URL}/sso/code/request",
        json={
            "client_id": client_id,
            "identifier": identifier,
            "redirect_uri": "http://localhost:3001/callback"
        }
    )
    if response.status_code == 200:
        data = response.json()
        print("✅ Код получен")
        print(f"   Code ID: {data['code_id'][:20]}...")
        print(f"   Code: {data['code']}")
        print(f"   Message: {data['message']}")
        print(f"   Expires In: {data['expires_in']} секунд (5 минут)")
        return data
    else:
        print(f"❌ Ошибка запроса кода: {response.json()}")
        raise Exception(f"Ошибка запроса кода: {response.status_code}")

def verify_code(client_id: str, client_secret: str, code_id: str, code: str) -> Dict:
    """Проверка кода и получение токенов"""
    print(f"\n✅ Проверка кода: {code}")
    response = requests.post(
        f"{BASE_URL}/sso/code/verify",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "code_id": code_id,
            "code": code
        }
    )
    if response.status_code == 200:
        data = response.json()
        print("✅ Код верный! Токены получены")
        print(f"   Access Token: {data['access_token'][:30]}...")
        print(f"   Refresh Token: {data['refresh_token'][:30]}...")
        print(f"   User: {data['user']['email']}")
        return data
    else:
        print(f"❌ Ошибка проверки кода: {response.json()}")
        raise Exception(f"Ошибка проверки кода: {response.status_code}")

def test_wrong_code(client_id: str, client_secret: str, code_id: str):
    """Тест с неверным кодом (проверка ограничения попыток)"""
    print(f"\n🧪 Тест с неверным кодом...")
    wrong_code = "000000"
    
    try:
        response = requests.post(
            f"{BASE_URL}/sso/code/verify",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code_id": code_id,
                "code": wrong_code
            }
        )
        if response.status_code == 200:
            print("⚠️  Неожиданно: код принят (это ошибка!)")
        else:
            error_data = response.json()
            print(f"✅ Ожидаемая ошибка: {error_data.get('detail', 'Неизвестная ошибка')}")
    except Exception as e:
        print(f"❌ Ошибка при тесте: {e}")

def main():
    """Основная функция тестирования Code flow"""
    print("="*60)
    print("🧪 ТЕСТИРОВАНИЕ CODE FLOW (ЭТАП 4 SSO)")
    print("="*60)
    
    try:
        # 1. Регистрация/вход пользователя
        user_email = "code_test@example.com"
        user_password = "test_password_123"
        user_full_name = "Code Test User"
        
        try:
            user_data = register_user(user_email, user_password, user_full_name)
        except:
            user_data = login_user(user_email, user_password)
        
        access_token = user_data["access_token"]
        print(f"\n✅ Токен пользователя получен: {access_token[:30]}...")
        
        # 2. Создание OAuth клиента
        client_data = create_oauth_client(access_token)
        client_id = client_data["client_id"]
        client_secret = client_data["client_secret"]
        
        # 3. Запрос кода по email
        print("\n" + "="*60)
        print("ШАГ 1: Запрос кода по email")
        print("="*60)
        code_data = request_code(client_id, user_email)
        code_id = code_data["code_id"]
        verification_code = code_data["code"]
        
        print(f"\n📋 ПОЛУЧЕННЫЙ КОД: {verification_code}")
        print(f"   Платформа должна показать этот код пользователю")
        print(f"   Пользователь вводит код на платформе")
        
        # Небольшая пауза перед проверкой
        input("\n⏸️  Нажмите Enter для проверки кода...")
        
        # 4. Проверка кода
        print("\n" + "="*60)
        print("ШАГ 2: Проверка кода")
        print("="*60)
        tokens = verify_code(client_id, client_secret, code_id, verification_code)
        
        print("\n" + "="*60)
        print("✅ CODE FLOW УСПЕШНО ЗАВЕРШЕН!")
        print("="*60)
        print(f"📧 Пользователь: {tokens['user']['email']}")
        print(f"🔑 Access Token: {tokens['access_token'][:50]}...")
        print(f"🔄 Refresh Token: {tokens['refresh_token'][:50]}...")
        print(f"⏰ Expires In: {tokens['expires_in']} секунд")
        
        # 5. Дополнительные тесты
        print("\n" + "="*60)
        print("🧪 ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ")
        print("="*60)
        
        # Тест 1: Запрос кода по имени
        print("\n📝 Тест 1: Запрос кода по имени пользователя")
        code_data2 = request_code(client_id, user_full_name)
        print(f"✅ Код получен: {code_data2['code']}")
        
        # Тест 2: Неверный код (ограничение попыток)
        print("\n📝 Тест 2: Попытка ввода неверного кода")
        test_wrong_code(client_id, client_secret, code_data2['code_id'])
        
        # Тест 3: Несуществующий пользователь (безопасность)
        print("\n📝 Тест 3: Запрос кода для несуществующего пользователя")
        fake_code_data = request_code(client_id, "nonexistent@example.com")
        print(f"✅ Фиктивный код получен (безопасность): {fake_code_data['code']}")
        print("   При проверке этот код будет отклонен, но не раскроет информацию о пользователе")
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

