/**
 * Скрипт для тестирования регистрации платформы через Life SSO
 * 
 * Что делает:
 * 1. Регистрирует платформу через API
 * 2. Открывает браузер с формой авторизации
 * 3. Пользователь входит через Life SSO
 * 4. После входа показывает результат (успешно/не успешно)
 */

const http = require('http');
const { exec } = require('child_process');
const url = require('url');
const querystring = require('querystring');

const API_BASE = 'http://localhost:8000';
const PLATFORM_PORT = 3001; // Порт для тестовой платформы
const PLATFORM_URL = `http://localhost:${PLATFORM_PORT}`;

// Данные для регистрации платформы
const platformData = {
  name: 'Тестовая Платформа',
  redirect_uri: `${PLATFORM_URL}/callback`,
  allowed_scopes: 'openid profile email'
};

// Хранилище данных
let clientCredentials = null;
let authCode = null;
let tokens = null;

console.log('🚀 Запуск тестового скрипта для регистрации платформы через Life SSO\n');

// Шаг 1: Регистрация платформы
async function registerPlatform() {
  return new Promise((resolve, reject) => {
    console.log('📝 Шаг 1: Регистрация платформы...');
    
    // Сначала нужно получить токен пользователя для регистрации платформы
    // Для теста используем существующего пользователя или создадим временного
    // Но сначала проверим, можем ли мы использовать публичный эндпоинт
    
    // Примечание: Эндпоинт /sso/clients требует авторизации
    // Скрипт автоматически выполнит логин при необходимости
    
    const postData = JSON.stringify(platformData);
    
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/sso/clients',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
        // 'Authorization': `Bearer ${accessToken}` // Если нужна авторизация
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          try {
            clientCredentials = JSON.parse(data);
            console.log('✅ Платформа успешно зарегистрирована!');
            console.log(`   📛 Название: ${clientCredentials.name}`);
            console.log(`   🆔 Client ID: ${clientCredentials.client_id}`);
            console.log(`   🔑 Client Secret: ${clientCredentials.client_secret.substring(0, 20)}...`);
            console.log(`   🔗 Redirect URI: ${clientCredentials.redirect_uri}\n`);
            resolve(clientCredentials);
          } catch (err) {
            console.error('❌ Ошибка парсинга ответа:', err);
            reject(err);
          }
        } else if (res.statusCode === 401) {
          // Нужна авторизация - сначала логинимся
          console.log('⚠️  Требуется авторизация. Выполняем вход...');
          loginUser().then(() => {
            // Повторяем запрос с токеном
            registerPlatformWithToken().then(resolve).catch(reject);
          }).catch(reject);
        } else {
          console.error('❌ Ошибка регистрации платформы:');
          console.error(`   Статус: ${res.statusCode}`);
          console.error(`   Ответ: ${data}`);
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    
    req.on('error', (err) => {
      console.error('❌ Ошибка запроса:', err);
      reject(err);
    });
    
    req.write(postData);
    req.end();
  });
}

// Логин пользователя для получения токена
async function loginUser() {
  return new Promise((resolve, reject) => {
    console.log('🔐 Выполняем вход для получения токена...');
    
    const loginData = JSON.stringify({
      email: 'test@example.com', // Замените на реальные данные
      password: 'test123' // Замените на реальный пароль
    });
    
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/login',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(loginData)
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 200) {
          try {
            const loginResult = JSON.parse(data);
            globalAccessToken = loginResult.access_token;
            console.log('✅ Вход выполнен успешно!\n');
            resolve(loginResult);
          } catch (err) {
            reject(err);
          }
        } else {
          console.error('❌ Ошибка входа:', data);
          reject(new Error(`Login failed: ${res.statusCode}`));
        }
      });
    });
    
    req.on('error', reject);
    req.write(loginData);
    req.end();
  });
}

let globalAccessToken = null;

// Регистрация платформы с токеном
async function registerPlatformWithToken() {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(platformData);
    
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/sso/clients',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
        'Authorization': `Bearer ${globalAccessToken}`
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          try {
            clientCredentials = JSON.parse(data);
            console.log('✅ Платформа успешно зарегистрирована!');
            console.log(`   📛 Название: ${clientCredentials.name}`);
            console.log(`   🆔 Client ID: ${clientCredentials.client_id}`);
            console.log(`   🔑 Client Secret: ${clientCredentials.client_secret.substring(0, 20)}...`);
            console.log(`   🔗 Redirect URI: ${clientCredentials.redirect_uri}\n`);
            resolve(clientCredentials);
          } catch (err) {
            reject(err);
          }
        } else {
          console.error('❌ Ошибка регистрации:', data);
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

// Шаг 2: Создаем сервер для callback платформы
function createCallbackServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const parsedUrl = url.parse(req.url, true);
      
      if (parsedUrl.pathname === '/callback') {
        authCode = parsedUrl.query.code;
        const state = parsedUrl.query.state;
        const error = parsedUrl.query.error;
        
        console.log('\n📥 Получен callback от Life SSO:');
        console.log(`   Code: ${authCode ? authCode.substring(0, 20) + '...' : 'нет'}`);
        console.log(`   State: ${state || 'нет'}`);
        console.log(`   Error: ${error || 'нет'}\n`);
        
        // Отправляем HTML ответ пользователю
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        
        if (error) {
          res.end(`
            <!DOCTYPE html>
            <html>
            <head>
              <title>Ошибка авторизации</title>
              <meta charset="utf-8">
              <style>
                body {
                  font-family: Arial, sans-serif;
                  max-width: 600px;
                  margin: 50px auto;
                  padding: 20px;
                  background: #fee;
                }
                h1 { color: #c00; }
              </style>
            </head>
            <body>
              <h1>❌ Ошибка авторизации</h1>
              <p>Ошибка: ${error}</p>
              <p>Вы можете закрыть это окно.</p>
            </body>
            </html>
          `);
          
          console.log('❌ Авторизация не прошла: ' + error);
          server.close();
          process.exit(1);
        } else if (authCode) {
          res.end(`
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
          `);
          
          // Обмениваем code на токены
          exchangeCodeForTokens(authCode).then(() => {
            server.close();
            resolve();
          }).catch((err) => {
            console.error('❌ Ошибка обмена токенов:', err);
            server.close();
            process.exit(1);
          });
        } else {
          res.end('<h1>Ошибка: код не получен</h1>');
          server.close();
          process.exit(1);
        }
      } else {
        res.writeHead(404);
        res.end('Not Found');
      }
    });
    
    server.listen(PLATFORM_PORT, () => {
      console.log(`🌐 Шаг 2: Создан callback сервер на ${PLATFORM_URL}/callback\n`);
      resolve(server);
    });
  });
}

// Шаг 3: Открываем браузер с формой авторизации
function openAuthorizationPage() {
  if (!clientCredentials) {
    throw new Error('Платформа не зарегистрирована');
  }
  
  const authUrl = new URL(`${API_BASE}/sso/authorize`);
  authUrl.searchParams.set('client_id', clientCredentials.client_id);
  authUrl.searchParams.set('redirect_uri', clientCredentials.redirect_uri);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('scope', 'openid profile email');
  authUrl.searchParams.set('state', 'test_state_123');
  
  const fullUrl = authUrl.toString();
  
  console.log('🌐 Шаг 3: Открываем форму авторизации в браузере...');
  console.log(`   URL: ${fullUrl}\n`);
  console.log('👤 Пожалуйста, войдите в Life SSO в открывшемся браузере.\n');
  
  // Открываем браузер (работает на Windows, Mac, Linux)
  const command = process.platform === 'win32' 
    ? `start ${fullUrl}`
    : process.platform === 'darwin'
    ? `open ${fullUrl}`
    : `xdg-open ${fullUrl}`;
  
  exec(command, (error) => {
    if (error) {
      console.error('❌ Ошибка открытия браузера:', error);
      console.log(`\n📋 Пожалуйста, откройте этот URL вручную:\n   ${fullUrl}\n`);
    }
  });
}

// Шаг 4: Обмениваем authorization code на токены
async function exchangeCodeForTokens(code) {
  return new Promise((resolve, reject) => {
    console.log('🔄 Шаг 4: Обмен authorization code на токены...');
    
    if (!clientCredentials) {
      return reject(new Error('Платформа не зарегистрирована'));
    }
    
    const postData = JSON.stringify({
      grant_type: 'authorization_code',
      code: code,
      client_id: clientCredentials.client_id,
      client_secret: clientCredentials.client_secret,
      redirect_uri: clientCredentials.redirect_uri
    });
    
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/sso/token',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 200) {
          try {
            tokens = JSON.parse(data);
            console.log('✅ Токены успешно получены!');
            console.log(`   🔑 Access Token: ${tokens.access_token.substring(0, 30)}...`);
            console.log(`   🔄 Refresh Token: ${tokens.refresh_token.substring(0, 30)}...`);
            console.log(`   👤 Пользователь: ${tokens.user.email} (${tokens.user.full_name})`);
            console.log(`   ⏰ Expires In: ${tokens.expires_in} секунд\n`);
            
            console.log('='.repeat(60));
            console.log('🎉 РЕГИСТРАЦИЯ И ВХОД НА ПЛАТФОРМУ ПРОШЛИ УСПЕШНО!');
            console.log('='.repeat(60));
            console.log('\n📊 Итоговые данные:');
            console.log(`   📛 Платформа: ${clientCredentials.name}`);
            console.log(`   🆔 Client ID: ${clientCredentials.client_id}`);
            console.log(`   👤 Пользователь: ${tokens.user.full_name} (${tokens.user.email})`);
            console.log(`   🔑 Access Token получен: ✅`);
            console.log(`   🔄 Refresh Token получен: ✅`);
            console.log('\n✅ Тест пройден успешно!\n');
            
            resolve(tokens);
          } catch (err) {
            console.error('❌ Ошибка парсинга токенов:', err);
            reject(err);
          }
        } else {
          console.error('❌ Ошибка обмена токенов:');
          console.error(`   Статус: ${res.statusCode}`);
          console.error(`   Ответ: ${data}`);
          
          console.log('\n❌ РЕГИСТРАЦИЯ ИЛИ ВХОД НА ПЛАТФОРМУ НЕ ПРОШЛИ!');
          console.log('='.repeat(60));
          console.log('\n📋 Причина ошибки:');
          try {
            const errorData = JSON.parse(data);
            console.log(`   ${errorData.detail || data}`);
          } catch {
            console.log(`   ${data}`);
          }
          console.log('\n');
          
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    
    req.on('error', (err) => {
      console.error('❌ Ошибка запроса:', err);
      reject(err);
    });
    
    req.write(postData);
    req.end();
  });
}

// Главная функция
async function main() {
  try {
    // Создаем callback сервер
    await createCallbackServer();
    
    // Регистрируем платформу
    await registerPlatform();
    
    // Открываем форму авторизации
    openAuthorizationPage();
    
    // Ждем callback (сервер обработает его автоматически)
    console.log('⏳ Ожидаем callback от Life SSO...\n');
    
  } catch (error) {
    console.error('\n❌ КРИТИЧЕСКАЯ ОШИБКА:', error.message);
    console.error('   Регистрация или вход на платформу не прошли!\n');
    process.exit(1);
  }
}

// Запуск
main();

