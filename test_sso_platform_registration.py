"""
Скрипт для тестирования регистрации платформы через Life SSO

Что делает:
1. Регистрирует платформу через API
2. Открывает браузер с формой авторизации
3. Пользователь входит через Life SSO
4. После входа показывает результат (успешно/не успешно)
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import requests
import json
import sys
import time
from threading import Thread

# Конфигурация
API_BASE = 'http://localhost:8000'
PLATFORM_PORT = 3001
PLATFORM_URL = f'http://localhost:{PLATFORM_PORT}'

# Данные для регистрации платформы
PLATFORM_DATA = {
    'name': 'Тестовая Платформа',
    'redirect_uri': f'{PLATFORM_URL}/callback',
    'allowed_scopes': 'openid profile email'
}

# Данные для входа (ИЗМЕНИТЕ НА СВОИ ИЛИ ОСТАВЬТЕ ДЛЯ АВТОРЕГИСТРАЦИИ!)
LOGIN_EMAIL = 'ede@mail.com'  # Замените на ваш email или оставьте для авторегистрации
LOGIN_PASSWORD = '123456'  # Замените на ваш пароль или оставьте для авторегистрации
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


def start_callback_server():
    """Запускает callback сервер в отдельном потоке"""
    handler = CallbackHandler
    
    with socketserver.TCPServer(("", PLATFORM_PORT), handler) as httpd:
        print(f'🌐 Шаг 2: Создан callback сервер на {PLATFORM_URL}/callback\n')
        httpd.serve_forever()


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
    """Выполняет вход пользователя для получения токена"""
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
            
            # Даем понятное сообщение
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
            print('✅ Платформа успешно зарегистрирована!')
            print(f'   📛 Название: {client_credentials["name"]}')
            print(f'   🆔 Client ID: {client_credentials["client_id"]}')
            secret_preview = client_credentials["client_secret"][:20] + '...'
            print(f'   🔑 Client Secret: {secret_preview}')
            print(f'   🔗 Redirect URI: {client_credentials["redirect_uri"]}\n')
            return client_credentials
        else:
            error_msg = response.text
            print(f'❌ Ошибка регистрации платформы:')
            print(f'   Статус: {response.status_code}')
            print(f'   Ответ: {error_msg}')
            raise Exception(f'HTTP {response.status_code}: {error_msg}')
    
    except requests.exceptions.RequestException as e:
        print(f'❌ Ошибка запроса: {e}')
        raise


def open_authorization_page():
    """Открывает браузер с формой авторизации"""
    if not client_credentials:
        raise Exception('Платформа не зарегистрирована')
    
    auth_url = f'{API_BASE}/sso/authorize'
    params = {
        'client_id': client_credentials['client_id'],
        'redirect_uri': client_credentials['redirect_uri'],
        'response_type': 'code',
        'scope': 'openid profile email',
        'state': 'test_state_123'
    }
    
    full_url = f'{auth_url}?{urllib.parse.urlencode(params)}'
    
    print('🌐 Шаг 3: Открываем форму авторизации в браузере...')
    print(f'   URL: {full_url}\n')
    print('👤 Пожалуйста, войдите в Life SSO в открывшемся браузере.\n')
    
    # Открываем браузер
    webbrowser.open(full_url)


def exchange_code_for_tokens(code):
    """Обменивает authorization code на токены"""
    global tokens
    
    if not client_credentials:
        raise Exception('Платформа не зарегистрирована')
    
    print('🔄 Шаг 4: Обмен authorization code на токены...')
    
    try:
        response = requests.post(
            f'{API_BASE}/sso/token',
            json={
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': client_credentials['client_id'],
                'client_secret': client_credentials['client_secret'],
                'redirect_uri': client_credentials['redirect_uri']
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            tokens = response.json()
            print('✅ Токены успешно получены!')
            token_preview = tokens['access_token'][:30] + '...'
            print(f'   🔑 Access Token: {token_preview}')
            refresh_preview = tokens['refresh_token'][:30] + '...'
            print(f'   🔄 Refresh Token: {refresh_preview}')
            user_info = tokens['user']
            print(f'   👤 Пользователь: {user_info["full_name"]} ({user_info["email"]})')
            print(f'   ⏰ Expires In: {tokens["expires_in"]} секунд\n')
            
            print('=' * 60)
            print('🎉 РЕГИСТРАЦИЯ И ВХОД НА ПЛАТФОРМУ ПРОШЛИ УСПЕШНО!')
            print('=' * 60)
            print('\n📊 Итоговые данные:')
            print(f'   📛 Платформа: {client_credentials["name"]}')
            print(f'   🆔 Client ID: {client_credentials["client_id"]}')
            print(f'   👤 Пользователь: {user_info["full_name"]} ({user_info["email"]})')
            print(f'   🔑 Access Token получен: ✅')
            print(f'   🔄 Refresh Token получен: ✅')
            print('\n✅ Тест пройден успешно!\n')
            
            return tokens
        else:
            error_msg = response.text
            print('❌ Ошибка обмена токенов:')
            print(f'   Статус: {response.status_code}')
            print(f'   Ответ: {error_msg}')
            
            print('\n❌ РЕГИСТРАЦИЯ ИЛИ ВХОД НА ПЛАТФОРМУ НЕ ПРОШЛИ!')
            print('=' * 60)
            print('\n📋 Причина ошибки:')
            try:
                error_data = response.json()
                print(f'   {error_data.get("detail", error_msg)}')
            except:
                print(f'   {error_msg}')
            print('\n')
            
            raise Exception(f'HTTP {response.status_code}: {error_msg}')
    
    except requests.exceptions.RequestException as e:
        print(f'❌ Ошибка запроса: {e}')
        raise


def main():
    """Главная функция"""
    global callback_received, callback_result
    
    try:
        print('🚀 Запуск тестового скрипта для регистрации платформы через Life SSO\n')
        
        # Запускаем callback сервер в отдельном потоке
        server_thread = Thread(target=start_callback_server, daemon=True)
        server_thread.start()
        
        # Даем серверу время на запуск
        time.sleep(1)
        
        # Регистрируем платформу
        register_platform()
        
        # Открываем форму авторизации
        open_authorization_page()
        
        # Ждем callback
        print('⏳ Ожидаем callback от Life SSO...\n')
        
        # Ожидаем callback (максимум 5 минут)
        timeout = 300  # 5 минут
        start_time = time.time()
        
        while not callback_received:
            time.sleep(0.5)
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print('❌ Таймаут ожидания callback')
                print('   Регистрация или вход на платформу не прошли!')
                sys.exit(1)
        
        # Проверяем результат callback
        if callback_result['error']:
            print(f'❌ Авторизация не прошла: {callback_result["error"]}')
            print('   Регистрация или вход на платформу не прошли!')
            sys.exit(1)
        
        if not callback_result['code']:
            print('❌ Authorization code не получен')
            print('   Регистрация или вход на платформу не прошли!')
            sys.exit(1)
        
        # Обмениваем code на токены
        exchange_code_for_tokens(callback_result['code'])
        
        # Успешное завершение
        sys.exit(0)
    
    except KeyboardInterrupt:
        print('\n\n⚠️  Скрипт прерван пользователем\n')
        sys.exit(1)
    except Exception as error:
        print(f'\n❌ КРИТИЧЕСКАЯ ОШИБКА: {error}')
        print('   Регистрация или вход на платформу не прошли!\n')
        sys.exit(1)


if __name__ == '__main__':
    main()

