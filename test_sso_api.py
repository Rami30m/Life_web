"""
Скрипт для тестирования SSO API (Этап 1)

Установка зависимостей:
    pip install requests

Запуск:
    python test_sso_api.py
"""

import requests
import json

# Базовый URL API
BASE_URL = "http://localhost:8000"

def print_response(title, response):
    """Красивый вывод ответа"""
    print("\n" + "="*60)
    print(f"📋 {title}")
    print("="*60)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print("="*60 + "\n")

def test_sso_api():
    """Тестирование SSO API"""
    
    print("🚀 ТЕСТИРОВАНИЕ SSO API (ЭТАП 1)")
    print("="*60)
    
    # ШАГ 1: Регистрация или вход пользователя
    print("\n1️⃣ ШАГ 1: Авторизация пользователя")
    
    # Вариант A: Регистрация (если пользователя нет)
    print("\n📝 Вариант A: Регистрация нового пользователя")
    register_data = {
        "full_name": "Test SSO User",
        "email": "test@sso.example.com",
        "phone": "+79991234567",
        "birth_date": "1990-01-01",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/register", json=register_data)
    print_response("Регистрация пользователя", response)
    
    if response.status_code != 200:
        # Если регистрация не удалась, пробуем войти
        print("\n🔐 Вариант B: Вход существующего пользователя")
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print_response("Вход пользователя", response)
    
    # Извлекаем токены
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens["access_token"]
        user_data = tokens["user"]
        
        print(f"✅ Авторизация успешна!")
        print(f"👤 Пользователь: {user_data['email']}")
        print(f"🔑 Access Token: {access_token[:20]}...")
        
        # ШАГ 2: Создание OAuth клиента
        print("\n2️⃣ ШАГ 2: Создание OAuth клиента")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        client_data = {
            "name": "Test Platform",
            "redirect_uri": "https://test-platform.com/callback",
            "allowed_scopes": "openid profile email"
        }
        
        response = requests.post(
            f"{BASE_URL}/sso/clients",
            json=client_data,
            headers=headers
        )
        print_response("Создание OAuth клиента", response)
        
        if response.status_code == 200:
            client_response = response.json()
            client_id = client_response["client_id"]
            client_secret = client_response["client_secret"]
            
            print("⚠️ ВАЖНО: Сохраните эти данные!")
            print(f"Client ID: {client_id}")
            print(f"Client Secret: {client_secret}")
            
            # ШАГ 3: Получение списка OAuth клиентов
            print("\n3️⃣ ШАГ 3: Получение списка OAuth клиентов")
            
            response = requests.get(
                f"{BASE_URL}/sso/clients",
                headers=headers
            )
            print_response("Список OAuth клиентов", response)
            
            if response.status_code == 200:
                clients = response.json()
                print(f"📊 Всего клиентов: {len(clients)}")
                for i, client in enumerate(clients, 1):
                    print(f"\n{i}. {client['name']}")
                    print(f"   ID: {client['client_id']}")
                    print(f"   Redirect URI: {client['redirect_uri']}")
                    print(f"   Scopes: {client['allowed_scopes']}")
                    print(f"   Active: {client['is_active']}")
            
            # ШАГ 4: Проверка без авторизации (должна быть ошибка)
            print("\n4️⃣ ШАГ 4: Проверка защиты эндпоинтов (без токена)")
            
            response = requests.get(f"{BASE_URL}/sso/clients")
            print_response("Запрос без токена (должна быть 401)", response)
            
            if response.status_code == 401:
                print("✅ Защита работает! Эндпоинт требует авторизации.")
        else:
            print("❌ Ошибка при создании OAuth клиента")
    else:
        print("❌ Ошибка авторизации. Проверьте данные.")

if __name__ == "__main__":
    try:
        test_sso_api()
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка: Не удалось подключиться к серверу.")
        print("💡 Убедитесь, что сервер запущен: uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

