"""
Скрипт для тестирования входа через Life SSO с переадресацией

Что делает:
1. Регистрирует платформу через API (если нужно)
2. Формирует URL для входа через SSO (GET /sso/authorize)
3. Открывает браузер с фронтендом Life SSO для входа
4. Ждет callback с authorization code
5. Обменивает code на токены    (POST /sso/token)
6. Показывает статус входа (успешно/не успешно)
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import requests
import json
import sys
import time
import socket
from threading import Thread

# Конфигурация
API_BASE = 'http://localhost:8000'
FRONTEND_BASE = 'http://localhost:3000'  # Фронтенд Life SSO
PLATFORM_PORT_START = 3002  # Начальный порт для поиска свободного
PLATFORM_PORT = None  # Будет установлен автоматически
PLATFORM_URL = None  # Будет установлен автоматически

# Данные для регистрации платформы (redirect_uri обновится после выбора порта)
PLATFORM_DATA = {
    'name': 'Тестовая Платформа для Входа',
    'redirect_uri': None,  # Будет установлен после выбора порта
    'allowed_scopes': 'openid profile email'
}

# Данные для входа (ИЗМЕНИТЕ НА СВОИ ИЛИ ОСТАВЬТЕ ДЛЯ АВТОРЕГИСТРАЦИИ!)
LOGIN_EMAIL = 'ede@mail.com'  # Замените на ваш email
LOGIN_PASSWORD = '123456'  # Замените на ваш пароль
AUTO_REGISTER_USER = True  # Если True, автоматически зарегистрирует пользователя если его нет

# Хранилище данных
client_credentials = None
auth_code = None
tokens = None
global_access_token = None
callback_received = False

# Результат callback
callback_result = {
    'code': None,
    'state': None,
    'error': None
}


class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик для callback сервера"""
    
    def do_GET(self):
        """Обработка GET запроса (callback от Life SSO)"""
        global callback_received, callback_result, auth_code
        
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if parsed_path.path == '/callback':
            # Получаем параметры из URL
            code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            error = query_params.get('error', [None])[0]
            
            callback_result['code'] = code
            callback_result['state'] = state
            callback_result['error'] = error
            
            auth_code = code
            callback_received = True
            
            print('\n📥 Получен callback от Life SSO:')
            print(f'   Code: {code[:20] + "..." if code else "нет"}')
            print(f'   State: {state or "нет"}')
            print(f'   Error: {error or "нет"}\n')
            
            # Отправляем HTML ответ пользователю
            if error:
                html_content = f'''
                <!DOCTYPE html>
                <html>
                <head>
                  <title>Ошибка авторизации</title>
                  <meta charset="utf-8">
                  <style>
                    body {{
                      font-family: Arial, sans-serif;
                      max-width: 600px;
                      margin: 50px auto;
                      padding: 20px;
                      background: #fee;
                    }}
                    h1 {{ color: #c00; }}
                  </style>
                </head>
                <body>
                  <h1>❌ Ошибка авторизации</h1>
                  <p>Ошибка: {error}</p>
                  <p>Вы можете закрыть это окно.</p>
                </body>
                </html>
                '''
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
                print(f'❌ Авторизация не прошла: {error}')
                return
            elif code:
                html_content = '''
                <!DOCTYPE html>
                <html>
                <head>
                  <title>Авторизация успешна</title>
                  <meta charset="utf-8">
                  <style>
                    body {
                      font-family: Arial, sans-serif;
                      max-width: 600px;
                      margin: 50px auto;
                      padding: 20px;
                      background: #efe;
                    }
                    h1 { color: #0c0; }
                  </style>
                </head>
                <body>
                  <h1>✅ Авторизация успешна!</h1>
                  <p>Получен authorization code. Ожидайте обмена на токены...</p>
                  <p>Вы можете закрыть это окно через несколько секунд.</p>
                  <script>
                    setTimeout(() => {
                      window.close();
                    }, 3000);
                  </script>
                </body>
                </html>
                '''
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                
                print('✅ Authorization code получен!\n')
                return
            else:
                html_content = '<h1>Ошибка: код не получен</h1>'
                self.send_response(400)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
                return
        
        # Для других путей возвращаем 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Отключаем логирование запросов"""
        pass


def find_free_port(start_port=3002, max_attempts=100):
    """Находит свободный порт, начиная с start_port"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise Exception(f"Не удалось найти свободный порт в диапазоне {start_port}-{start_port + max_attempts}")


def start_callback_server():
    """Запускает callback сервер в отдельном потоке"""
    if PLATFORM_PORT is None:
        raise Exception("Порт не выбран! Сначала вызовите find_free_port()")
    
    handler = CallbackHandler
    
    try:
        with socketserver.TCPServer(("", PLATFORM_PORT), handler) as httpd:
            print(f'🌐 Шаг 2: Создан callback сервер на {PLATFORM_URL}/callback\n')
            httpd.serve_forever()
    except OSError as e:
        # Если порт всё же занят (редкий случай), выводим ошибку
        if "10048" in str(e) or "address already in use" in str(e).lower():
            print(f'❌ Ошибка: Порт {PLATFORM_PORT} занят после выбора!')
            print(f'   Попробуйте запустить скрипт снова или завершите процесс на порту {PLATFORM_PORT}')
            raise
        else:
            raise


def register_user_if_needed():
    """Регистрирует пользователя если его нет (только если AUTO_REGISTER_USER = True)"""
    if not AUTO_REGISTER_USER:
        return False
    
    print('📝 Попытка регистрации пользователя (если не существует)...')
    
    try:
        response = requests.post(
            f'{API_BASE}/register',
            json={
                'email': LOGIN_EMAIL,
                'password': LOGIN_PASSWORD,
                'full_name': 'Test User',
                'phone': '+7 777 123 4567',
                'birth_date': '1990-01-01'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print('✅ Пользователь успешно зарегистрирован!\n')
            return True
        elif response.status_code == 400:
            # Пользователь уже существует - это нормально
            error_data = response.json()
            if 'уже зарегистрирован' in error_data.get('detail', '').lower():
                print('ℹ️  Пользователь уже существует, продолжаем...\n')
                return True
            else:
                print(f'⚠️  Ошибка регистрации: {error_data.get("detail", "Неизвестная ошибка")}')
                return False
        else:
            error_msg = response.text
            print(f'⚠️  Не удалось зарегистрировать пользователя: {error_msg}')
            return False
    
    except requests.exceptions.RequestException as e:
        print(f'⚠️  Ошибка запроса при регистрации: {e}')
        return False


def login_user():
    """Выполняет вход пользователя для получения токена (для регистрации платформы)"""
    global global_access_token
    
    print('🔐 Выполняем вход для получения токена...')
    
    # Если включена авторегистрация, попробуем зарегистрировать пользователя
    if AUTO_REGISTER_USER:
        register_user_if_needed()
    
    try:
        response = requests.post(
            f'{API_BASE}/login',
            json={
                'email': LOGIN_EMAIL,
                'password': LOGIN_PASSWORD
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            login_result = response.json()
            global_access_token = login_result.get('access_token')
            print('✅ Вход выполнен успешно!\n')
            return login_result
        else:
            error_msg = response.text
            print(f'❌ Ошибка входа: {error_msg}')
            
            print('\n' + '='*60)
            print('❌ ОШИБКА: Неверные данные для входа!')
            print('='*60)
            print('\n📋 Что делать:')
            print('   1. Убедитесь, что пользователь существует в системе Life SSO')
            print('   2. Или измените LOGIN_EMAIL и LOGIN_PASSWORD в скрипте')
            print('   3. Или установите AUTO_REGISTER_USER = True для авторегистрации')
            print(f'\n   Текущие данные:')
            print(f'   Email: {LOGIN_EMAIL}')
            print(f'   Password: {LOGIN_PASSWORD}')
            print('\n')
            
            raise Exception(f'Login failed: {response.status_code}')
    
    except requests.exceptions.RequestException as e:
        print(f'❌ Ошибка запроса при входе: {e}')
        raise


def register_platform():
    """Регистрирует платформу через API"""
    global client_credentials
    
    print('📝 Шаг 1: Регистрация платформы...')
    
    try:
        # Сначала пытаемся зарегистрировать без токена
        response = requests.post(
            f'{API_BASE}/sso/clients',
            json=PLATFORM_DATA,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 401:
            # Требуется авторизация - логинимся
            print('⚠️  Требуется авторизация. Выполняем вход...')
            login_user()
            
            # Повторяем запрос с токеном
            response = requests.post(
                f'{API_BASE}/sso/clients',
                json=PLATFORM_DATA,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {global_access_token}'
                }
            )
        
        if response.status_code in (200, 201):
            client_credentials = response.json()
            print('✅ Платформа зарегистрирована!')
            print(f'   Client ID: {client_credentials.get("client_id", "не получен")}')
            print(f'   Name: {client_credentials.get("name", "не получено")}\n')
            return True
        else:
            error_msg = response.text
            print(f'❌ Ошибка регистрации платформы: {error_msg}')
            return False
    
    except requests.exceptions.RequestException as e:
        print(f'❌ Ошибка запроса при регистрации платформы: {e}')
        return False


def get_authorize_url():
    """Формирует URL для авторизации через SSO"""
    if not client_credentials:
        raise Exception("Платформа не зарегистрирована!")
    
    client_id = client_credentials.get('client_id')
    redirect_uri = PLATFORM_DATA['redirect_uri']
    state = 'test_state_12345'  # Можно использовать случайное значение
    scope = PLATFORM_DATA['allowed_scopes']
    
    # Формируем URL для фронтенда Life SSO
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'state': state,
        'scope': scope
    }
    
    authorize_url = f'{FRONTEND_BASE}/sso/authorize?' + urllib.parse.urlencode(params)
    
    print('🔗 Шаг 3: Формирование URL для авторизации...')
    print(f'   Client ID: {client_id}')
    print(f'   Redirect URI: {redirect_uri}')
    print(f'   State: {state}')
    print(f'   Scope: {scope}')
    print(f'\n📎 URL для входа: {authorize_url}\n')
    
    return authorize_url, state


def open_authorize_page(authorize_url):
    """Открывает страницу авторизации в браузере"""
    print('🌐 Шаг 4: Открываем страницу авторизации в браузере...')
    print('   ⏳ Ожидаем входа пользователя на фронтенде Life SSO...\n')
    
    webbrowser.open(authorize_url)


def wait_for_callback(timeout=300):
    """Ожидает callback с authorization code"""
    global callback_received
    
    print('⏳ Ожидание callback с authorization code...')
    print(f'   (таймаут: {timeout} секунд)\n')
    
    start_time = time.time()
    while not callback_received:
        if time.time() - start_time > timeout:
            print('❌ Таймаут ожидания callback')
            return False
        time.sleep(0.5)
    
    return True


def exchange_code_for_tokens():
    """Обменивает authorization code на токены"""
    global tokens
    
    if not auth_code or not client_credentials:
        print('❌ Нет authorization code или client credentials')
        return False
    
    print('🔄 Шаг 5: Обмен authorization code на токены...')
    
    client_id = client_credentials.get('client_id')
    client_secret = client_credentials.get('client_secret')
    
    if not client_secret:
        print('❌ Client secret не найден!')
        return False
    
    try:
        response = requests.post(
            f'{API_BASE}/sso/token',
            data={
                'grant_type': 'authorization_code',
                'code': auth_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': PLATFORM_DATA['redirect_uri']
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code == 200:
            tokens = response.json()
            print('✅ Токены получены успешно!')
            print(f'   Access Token: {tokens.get("access_token", "не получен")[:30]}...')
            print(f'   Token Type: {tokens.get("token_type", "не получен")}')
            print(f'   Expires In: {tokens.get("expires_in", "не получено")} секунд\n')
            
            # Если есть user в ответе - выводим информацию
            if 'user' in tokens:
                user = tokens['user']
                print('👤 Информация о пользователе:')
                print(f'   ID: {user.get("id", "не получен")}')
                print(f'   Email: {user.get("email", "не получен")}')
                print(f'   Имя: {user.get("full_name", "не получено")}\n')
            
            return True
        else:
            error_msg = response.text
            print(f'❌ Ошибка обмена code на токены: {error_msg}')
            return False
    
    except requests.exceptions.RequestException as e:
        print(f'❌ Ошибка запроса при обмене токенов: {e}')
        return False


def show_final_status():
    """Показывает итоговый статус теста"""
    print('\n' + '='*60)
    print('📊 ИТОГОВЫЙ СТАТУС ТЕСТА')
    print('='*60)
    
    if callback_result.get('error'):
        print('❌ Тест НЕ ПРОШЕЛ')
        print(f'   Ошибка: {callback_result["error"]}')
    elif tokens:
        print('✅ Тест ПРОШЕЛ УСПЕШНО!')
        print(f'   Authorization Code получен: {"Да" if auth_code else "Нет"}')
        print(f'   Токены получены: {"Да" if tokens else "Нет"}')
        print(f'   Access Token: {"Есть" if tokens.get("access_token") else "Нет"}')
        print(f'   Refresh Token: {"Есть" if tokens.get("refresh_token") else "Нет"}')
    elif auth_code:
        print('⚠️  Тест ЧАСТИЧНО ПРОШЕЛ')
        print('   Authorization Code получен, но токены не обменяны')
    else:
        print('❌ Тест НЕ ПРОШЕЛ')
        print('   Authorization Code не получен')
    
    print('='*60 + '\n')


def main():
    """Основная функция теста"""
    print('\n' + '='*60)
    print('🧪 ТЕСТ ВХОДА ЧЕРЕЗ LIFE SSO С ПЕРЕАДРЕСАЦИЕЙ')
    print('='*60 + '\n')
    
    try:
        # Шаг 0: Выбор свободного порта для callback сервера
        global PLATFORM_PORT, PLATFORM_URL
        try:
            PLATFORM_PORT = find_free_port(PLATFORM_PORT_START)
            PLATFORM_URL = f'http://localhost:{PLATFORM_PORT}'
            PLATFORM_DATA['redirect_uri'] = f'{PLATFORM_URL}/callback'
            print(f'🔍 Выбран свободный порт: {PLATFORM_PORT}')
            print(f'   Callback URL: {PLATFORM_DATA["redirect_uri"]}\n')
        except Exception as e:
            print(f'❌ Не удалось найти свободный порт: {e}')
            return
        
        # Шаг 1: Регистрация платформы (с правильным redirect_uri)
        if not register_platform():
            print('❌ Не удалось зарегистрировать платформу')
            return
        
        # Шаг 2: Запуск callback сервера
        callback_thread = Thread(target=start_callback_server, daemon=True)
        callback_thread.start()
        time.sleep(1.5)  # Даем время серверу запуститься
        
        # Шаг 3: Формирование URL для авторизации
        authorize_url, state = get_authorize_url()
        
        # Шаг 4: Открытие страницы авторизации
        open_authorize_page(authorize_url)
        
        # Шаг 5: Ожидание callback
        if not wait_for_callback():
            show_final_status()
            return
        
        # Шаг 6: Обмен code на токены
        if exchange_code_for_tokens():
            print('✅ Все шаги выполнены успешно!\n')
        else:
            print('❌ Ошибка при обмене code на токены\n')
        
        # Итоговый статус
        show_final_status()
        
    except KeyboardInterrupt:
        print('\n\n⚠️  Тест прерван пользователем')
    except Exception as e:
        print(f'\n❌ Критическая ошибка: {e}')
        import traceback
        traceback.print_exc()
        show_final_status()


if __name__ == '__main__':
    main()

