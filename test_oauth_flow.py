"""
Скрипт для тестирования OAuth 2.0 Authorization Code Flow (Этап 2)

Установка зависимостей:
    pip install requests

Запуск:
    python test_oauth_flow.py
"""

import requests
import json
import webbrowser
from urllib.parse import parse_qs, urlparse, urlencode

# Базовый URL API
BASE_URL = "http://localhost:8000"

def print_section(title):
    """Красивый вывод секции"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_response(response, title="Ответ"):
    """Красивый вывод ответа"""
    print(f"\n📋 {title}:")
    print(f"   Status: {response.status_code}")
    try:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=4, ensure_ascii=False)}")
        return data
    except:
        print(f"   Response: {response.text}")
        return None

def test_oauth_flow():
    """Полный тест OAuth 2.0 Authorization Code Flow"""
    
    print_section("🚀 ТЕСТИРОВАНИЕ OAUTH 2.0 AUTHORIZATION CODE FLOW")
    
    # ========== ШАГ 1: Авторизация пользователя ==========
    print_section("ШАГ 1: Авторизация пользователя")
    
    # Регистрация или вход
    print("\n📝 Регистрация нового пользователя...")
    register_data = {
        "full_name": "OAuth Test User",
        "email": "oauth-test@example.com",
        "phone": "+79991234567",
        "birth_date": "1990-01-01",
        "password": "TestPass123!"
    }
    
    response = requests.post(f"{BASE_URL}/register", json=register_data)
    result = print_response(response, "Регистрация")
    
    if response.status_code != 200:
        print("\n🔐 Пользователь уже существует, пробуем войти...")
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        result = print_response(response, "Вход")
    
    if response.status_code != 200:
        print("\n❌ ОШИБКА: Не удалось авторизоваться!")
        return
    
    access_token = result["access_token"]
    print(f"\n✅ Авторизация успешна!")
    print(f"   🔑 Access Token: {access_token[:30]}...")
    
    # ========== ШАГ 2: Создание OAuth клиента ==========
    print_section("ШАГ 2: Создание OAuth клиента")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    client_data = {
        "name": "Test Platform",
        "redirect_uri": "http://localhost:3001/callback",
        "allowed_scopes": "openid profile email"
    }
    
    print(f"\n📤 Отправка запроса...")
    response = requests.post(
        f"{BASE_URL}/sso/clients",
        json=client_data,
        headers=headers
    )
    
    client_result = print_response(response, "Создание OAuth клиента")
    
    if response.status_code != 200:
        print("\n❌ ОШИБКА: Не удалось создать OAuth клиента!")
        return
    
    client_id = client_result["client_id"]
    client_secret = client_result["client_secret"]
    
    print(f"\n⚠️  ВАЖНО! Сохраните эти данные:")
    print(f"   🆔 Client ID: {client_id}")
    print(f"   🔑 Client Secret: {client_secret}")
    
    input("\n⏸️  Нажмите Enter для продолжения...")
    
    # ========== ШАГ 3: Инициация OAuth flow ==========
    print_section("ШАГ 3: Инициация OAuth flow")
    
    state = "test_state_12345"
    redirect_uri = client_data["redirect_uri"]
    scope = "openid profile email"
    
    authorize_url = (
        f"{BASE_URL}/sso/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"state={state}&"
        f"scope={scope}"
    )
    
    print(f"\n🔗 URL для авторизации:")
    print(f"   {authorize_url}")
    
    print(f"\n🌐 Открываю браузер для входа...")
    print(f"   (Или скопируйте URL выше и откройте вручную)")
    
    try:
        webbrowser.open(authorize_url)
    except:
        print("   ⚠️  Не удалось открыть браузер автоматически")
    
    print(f"\n📝 Инструкции:")
    print(f"   1. В открывшейся форме введите:")
    print(f"      Email: {register_data['email']}")
    print(f"      Password: {register_data['password']}")
    print(f"   2. После входа вас перенаправит на: {redirect_uri}?code=...")
    print(f"   3. Скопируйте ВЕСЬ URL из адресной строки браузера (после перенаправления)")
    
    url_input = input("\n📋 Вставьте полный URL после перенаправления: ").strip()
    
    if not url_input:
        print("\n❌ ОШИБКА: URL не введен!")
        return
    
    # Извлекаем authorization code из URL
    try:
        # Если пользователь ввел полный URL
        if url_input.startswith('http'):
            # Парсим URL и извлекаем параметр code
            parsed = urlparse(url_input)
            query_params = parse_qs(parsed.query)
            
            if 'code' not in query_params:
                print("\n❌ ОШИБКА: В URL не найден параметр 'code'")
                print(f"   Проверьте, что вы скопировали правильный URL")
                print(f"   Ожидается URL вида: {redirect_uri}?code=...&state=...")
                return
            
            authorization_code = query_params['code'][0]
            
            # Проверяем state (если есть)
            if 'state' in query_params:
                returned_state = query_params['state'][0]
                if returned_state != state:
                    print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЕ: State не совпадает!")
                    print(f"   Ожидался: {state}")
                    print(f"   Получен: {returned_state}")
                    print(f"   Продолжаем, но это может быть CSRF атака!")
            
            print(f"\n✅ Извлечен authorization code: {authorization_code[:20]}...")
            
        elif 'code=' in url_input or '&' in url_input or '?' in url_input:
            # Пользователь ввел часть URL (например: code=xxx&state=yyy)
            # Парсим как query string
            if url_input.startswith('?'):
                url_input = url_input[1:]  # Убираем ведущий ?
            
            # Если это не полный URL, добавляем базовый путь для парсинга
            fake_url = f"http://dummy.com?{url_input}" if not url_input.startswith('http') else url_input
            parsed = urlparse(fake_url)
            query_params = parse_qs(parsed.query)
            
            if 'code' not in query_params:
                print("\n❌ ОШИБКА: Не найден параметр 'code'")
                print(f"   Попробуйте скопировать только значение после 'code='")
                authorization_code = input("📋 Введите authorization code (только код): ").strip()
            else:
                authorization_code = query_params['code'][0]
            
            if not authorization_code:
                print("\n❌ ОШИБКА: Authorization code не найден!")
                return
                
            print(f"\n✅ Извлечен authorization code: {authorization_code[:20]}...")
            
        else:
            # Пользователь ввел только сам код (или код с лишними символами)
            # Очищаем от возможных лишних символов
            authorization_code = url_input.strip()
            
            # Если есть = или &, извлекаем только код
            if '=' in authorization_code:
                authorization_code = authorization_code.split('=')[-1]
            if '&' in authorization_code:
                authorization_code = authorization_code.split('&')[0]
            
            print(f"\n✅ Используется authorization code: {authorization_code[:20]}...")
            
    except Exception as e:
        print(f"\n❌ ОШИБКА при парсинге URL: {e}")
        print(f"   Попробуйте ввести только сам код (без URL и параметров)")
        authorization_code = input("📋 Введите authorization code: ").strip()
        
        if not authorization_code:
            print("\n❌ ОШИБКА: Authorization code не введен!")
            return
    
    # ========== ШАГ 4: Обмен code на токены ==========
    print_section("ШАГ 4: Обмен authorization code на токены")
    
    token_data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }
    
    print(f"\n📤 Отправка запроса на обмен токена...")
    print(f"\n🔍 Отладочная информация:")
    print(f"   Code (первые 30 символов): {authorization_code[:30]}...")
    print(f"   Code длина: {len(authorization_code)} символов")
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Redirect URI: {redirect_uri}")
    
    response = requests.post(
        f"{BASE_URL}/sso/token",
        json=token_data
    )
    
    token_result = print_response(response, "Обмен токена")
    
    if response.status_code != 200:
        print("\n❌ ОШИБКА: Не удалось обменять code на токены!")
        error_detail = token_result.get("detail", "Неизвестная ошибка") if token_result else response.text
        print(f"\n📋 Детали ошибки: {error_detail}")
        
        print("\n💡 Возможные причины и решения:")
        print("   1. Code уже использован (одноразовый)")
        print("      → Решение: Создайте новый authorization flow")
        print("   2. Code истек (живет 10 минут)")
        print("      → Решение: Повторите авторизацию быстрее")
        print("   3. Неверный client_secret")
        print("      → Решение: Проверьте, что используете правильный client_secret")
        print("   4. Неверный redirect_uri")
        print("      → Решение: Убедитесь, что redirect_uri совпадает с зарегистрированным")
        print("   5. Code содержит лишние символы")
        print("      → Решение: Убедитесь, что скопировали только сам code (без &state=...)")
        
        print(f"\n🔍 Отладочная информация отправленных данных:")
        print(f"   Полный code: {authorization_code}")
        print(f"   Client ID: {client_id}")
        print(f"   Redirect URI: {redirect_uri}")
        
        return
    
    print(f"\n✅ УСПЕХ! OAuth flow завершен!")
    print(f"\n📊 Полученные данные:")
    print(f"   🔑 Access Token: {token_result['access_token'][:30]}...")
    print(f"   🔄 Refresh Token: {token_result['refresh_token'][:30]}...")
    print(f"   👤 User: {token_result['user']['full_name']} ({token_result['user']['email']})")
    print(f"   ⏱️  Expires In: {token_result['expires_in']} секунд")
    
    # ========== ШАГ 5: Проверка защиты ==========
    print_section("ШАГ 5: Проверка защиты")
    
    print(f"\n🛡️  Тест 1: Повторное использование code (должна быть ошибка)")
    response = requests.post(
        f"{BASE_URL}/sso/token",
        json=token_data
    )
    
    if response.status_code == 400:
        print(f"   ✅ Защита работает! Code нельзя использовать дважды.")
    else:
        print(f"   ⚠️  Неожиданный ответ: {response.status_code}")
    
    print(f"\n🛡️  Тест 2: Неверный client_secret (должна быть ошибка)")
    bad_token_data = token_data.copy()
    bad_token_data["client_secret"] = "wrong_secret"
    response = requests.post(
        f"{BASE_URL}/sso/token",
        json=bad_token_data
    )
    
    if response.status_code == 401:
        print(f"   ✅ Защита работает! Неверный client_secret отклонен.")
    else:
        print(f"   ⚠️  Неожиданный ответ: {response.status_code}")
    
    print_section("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print(f"\n✅ Все этапы OAuth 2.0 Authorization Code Flow протестированы!")

if __name__ == "__main__":
    try:
        test_oauth_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Ошибка: Не удалось подключиться к серверу.")
        print("💡 Убедитесь, что сервер запущен:")
        print("   cd 'Life back2'")
        print("   uvicorn main:app --reload")
    except KeyboardInterrupt:
        print("\n\n⚠️  Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

