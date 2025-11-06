"""
Скрипт для регистрации платформы в Life SSO и получения client_id и client_secret

Использование:
1. Запустите скрипт
2. Введите данные платформы (название, redirect_uri)
3. Скопируйте client_id и client_secret в .env файл вашей платформы
"""

import requests
import sys

# Конфигурация
API_BASE = 'http://localhost:8000'

# Данные для входа в Life SSO (для регистрации платформы требуется авторизация)
LOGIN_EMAIL = 'ede@mail.com'  # Замените на ваш email
LOGIN_PASSWORD = '123456'  # Замените на ваш пароль
AUTO_REGISTER_USER = True  # Если True, автоматически зарегистрирует пользователя если его нет


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
                'full_name': 'Platform Admin',
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
            access_token = login_result.get('access_token')
            print('✅ Вход выполнен успешно!\n')
            return access_token
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


def register_platform(access_token, platform_name, redirect_uri, allowed_scopes='openid profile email'):
    """Регистрирует платформу в Life SSO и получает client_id и client_secret"""
    print('📝 Регистрация платформы в Life SSO...')
    print(f'   Название: {platform_name}')
    print(f'   Redirect URI: {redirect_uri}')
    print(f'   Scopes: {allowed_scopes}\n')
    
    try:
        response = requests.post(
            f'{API_BASE}/sso/clients',
            json={
                'name': platform_name,
                'redirect_uri': redirect_uri,
                'allowed_scopes': allowed_scopes
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        if response.status_code in (200, 201):
            client_data = response.json()
            print('✅ Платформа успешно зарегистрирована!\n')
            return client_data
        else:
            error_msg = response.text
            print(f'❌ Ошибка регистрации платформы: {error_msg}')
            return None
    
    except requests.exceptions.RequestException as e:
        print(f'❌ Ошибка запроса при регистрации платформы: {e}')
        return None


def main():
    """Основная функция"""
    print('\n' + '='*60)
    print('🔐 РЕГИСТРАЦИЯ ПЛАТФОРМЫ В LIFE SSO')
    print('='*60 + '\n')
    
    # Запрашиваем данные платформы
    print('📋 Введите данные платформы:\n')
    
    platform_name = input('Название платформы: ').strip()
    if not platform_name:
        print('❌ Название платформы не может быть пустым!')
        return
    
    redirect_uri = input('Redirect URI (например: http://localhost:3001/callback): ').strip()
    if not redirect_uri:
        print('❌ Redirect URI не может быть пустым!')
        return
    
    # Проверяем формат redirect_uri
    if not redirect_uri.startswith('http://') and not redirect_uri.startswith('https://'):
        print('⚠️  Внимание: Redirect URI должен начинаться с http:// или https://')
        confirm = input('Продолжить? (y/n): ').strip().lower()
        if confirm != 'y':
            return
    
    scopes_input = input('Scopes (по умолчанию: openid profile email, нажмите Enter для пропуска): ').strip()
    allowed_scopes = scopes_input if scopes_input else 'openid profile email'
    
    print('\n' + '-'*60 + '\n')
    
    try:
        # Шаг 1: Вход в Life SSO
        access_token = login_user()
        if not access_token:
            print('❌ Не удалось получить токен доступа')
            return
        
        # Шаг 2: Регистрация платформы
        client_data = register_platform(access_token, platform_name, redirect_uri, allowed_scopes)
        if not client_data:
            print('❌ Не удалось зарегистрировать платформу')
            return
        
        # Шаг 3: Вывод результатов
        print('\n' + '='*60)
        print('✅ РЕГИСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!')
        print('='*60 + '\n')
        
        client_id = client_data.get('client_id')
        client_secret = client_data.get('client_secret')
        
        print('📋 Скопируйте эти данные в .env файл вашей платформы:\n')
        print('-'*60)
        print(f'LIFE_SSO_CLIENT_ID={client_id}')
        print(f'LIFE_SSO_CLIENT_SECRET={client_secret}')
        print(f'LIFE_SSO_REDIRECT_URI={redirect_uri}')
        print(f'LIFE_SSO_API_BASE={API_BASE}')
        print('-'*60)
        
        print('\n⚠️  ВАЖНО:')
        print('   - Сохраните client_secret в безопасном месте!')
        print('   - Он больше не будет показан!')
        print('   - Если потеряете - перерегистрируйте платформу')
        
        print('\n📝 Дополнительная информация:')
        print(f'   Название платформы: {client_data.get("name", "не получено")}')
        print(f'   Redirect URI: {client_data.get("redirect_uri", "не получено")}')
        print(f'   Разрешенные scopes: {client_data.get("allowed_scopes", "не получено")}')
        print('\n')
        
    except KeyboardInterrupt:
        print('\n\n❌ Регистрация отменена пользователем')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ Ошибка: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()

