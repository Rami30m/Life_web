# 🔧 Life SSO - Примеры интеграции

Этот документ содержит готовые примеры кода для интеграции с Life SSO.

---

## JavaScript (Node.js + Express)

### Полный пример

```javascript
const express = require('express');
const axios = require('axios');
const session = require('express-session');

const app = express();
app.use(session({ secret: 'your-secret-key' }));

const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const REDIRECT_URI = 'http://localhost:3001/callback';
const SSO_BASE_URL = 'http://localhost:8000';

// 1. Редирект на Life SSO
app.get('/login', (req, res) => {
  const state = Math.random().toString(36).substring(7);
  req.session.oauth_state = state;
  
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    state: state,
    scope: 'openid profile email'
  });
  
  res.redirect(`${SSO_BASE_URL}/sso/authorize?${params}`);
});

// 2. Callback обработка
app.get('/callback', async (req, res) => {
  const { code, state } = req.query;
  
  // Проверка CSRF
  if (state !== req.session.oauth_state) {
    return res.status(400).send('Invalid state parameter');
  }
  
  try {
    // Обмен code на токены
    const response = await axios.post(`${SSO_BASE_URL}/sso/token`, {
      grant_type: 'authorization_code',
      code: code,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      redirect_uri: REDIRECT_URI
    });
    
    // Сохраняем токены в сессию
    req.session.accessToken = response.data.access_token;
    req.session.refreshToken = response.data.refresh_token;
    req.session.user = response.data.user;
    
    res.redirect('/dashboard');
  } catch (error) {
    console.error('Token exchange error:', error.response?.data);
    res.status(500).send('Authentication failed');
  }
});

// 3. Защищенный маршрут
app.get('/dashboard', async (req, res) => {
  if (!req.session.accessToken) {
    return res.redirect('/login');
  }
  
  // Используем токен для запросов к API
  try {
    const userResponse = await axios.get(`${SSO_BASE_URL}/me`, {
      headers: {
        'Authorization': `Bearer ${req.session.accessToken}`
      }
    });
    
    res.json({
      message: 'Welcome to dashboard!',
      user: userResponse.data
    });
  } catch (error) {
    // Токен истек, нужно переавторизоваться
    if (error.response?.status === 401) {
      return res.redirect('/login');
    }
    res.status(500).send('Error fetching user data');
  }
});

app.listen(3001, () => {
  console.log('Platform running on http://localhost:3001');
});
```

---

## Python (Flask)

```python
from flask import Flask, redirect, request, session, jsonify
import requests
import secrets

app = Flask(__name__)
app.secret_key = 'your-secret-key'

CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'http://localhost:3001/callback'
SSO_BASE_URL = 'http://localhost:8000'

@app.route('/login')
def login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': state,
        'scope': 'openid profile email'
    }
    
    url = f'{SSO_BASE_URL}/sso/authorize?' + '&'.join([f'{k}={v}' for k, v in params.items()])
    return redirect(url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Проверка CSRF
    if state != session.get('oauth_state'):
        return 'Invalid state parameter', 400
    
    # Обмен code на токены
    response = requests.post(
        f'{SSO_BASE_URL}/sso/token',
        json={
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI
        }
    )
    
    if response.status_code != 200:
        return 'Token exchange failed', 500
    
    data = response.json()
    session['access_token'] = data['access_token']
    session['refresh_token'] = data['refresh_token']
    session['user'] = data['user']
    
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'access_token' not in session:
        return redirect('/login')
    
    # Используем токен для запросов
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    user_response = requests.get(f'{SSO_BASE_URL}/me', headers=headers)
    
    if user_response.status_code == 401:
        return redirect('/login')
    
    return jsonify({
        'message': 'Welcome to dashboard!',
        'user': user_response.json()
    })

if __name__ == '__main__':
    app.run(port=3001)
```

---

## QR Code Flow (JavaScript)

```javascript
// Инициализация QR сессии
async function initiateQRLogin() {
  const response = await fetch('http://localhost:8000/sso/qr/initiate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      client_id: 'your_client_id',
      scope: 'openid profile email'
    })
  });
  
  const data = await response.json();
  
  // Генерируем QR код
  QRCode.toCanvas(document.getElementById('qr-canvas'), data.verification_uri_complete);
  
  // Показываем user_code
  document.getElementById('user-code').textContent = data.user_code;
  
  // Начинаем polling
  pollQRStatus(data.device_code);
}

// Polling статуса
async function pollQRStatus(deviceCode) {
  const maxAttempts = 120; // 10 минут
  let attempts = 0;
  
  const poll = async () => {
    attempts++;
    
    if (attempts > maxAttempts) {
      alert('QR-код истек. Пожалуйста, обновите страницу.');
      return;
    }
    
    try {
      const response = await fetch('http://localhost:8000/sso/qr/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          device_code: deviceCode,
          client_id: 'your_client_id',
          client_secret: 'your_client_secret' // Только на бэкенде!
        })
      });
      
      const data = await response.json();
      
      if (data.status === 'authorized') {
        // Успех!
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('refreshToken', data.refresh_token);
        window.location.href = '/dashboard';
      } else if (data.status === 'pending') {
        // Продолжаем polling
        setTimeout(poll, 5000);
      } else {
        // Ошибка
        alert('Ошибка авторизации: ' + data.message);
      }
    } catch (error) {
      console.error('Polling error:', error);
      setTimeout(poll, 5000);
    }
  };
  
  poll();
}
```

---

## Code Flow (JavaScript)

```javascript
// Запрос кода
async function requestCode() {
  const email = document.getElementById('email').value;
  
  const response = await fetch('http://localhost:8000/sso/code/request', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      client_id: 'your_client_id',
      identifier: email
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    alert(data.message); // "Откройте Life SSO..."
    // Показываем поле для ввода кода
    document.getElementById('code-input').style.display = 'block';
    document.getElementById('code-id').value = data.code_id;
  } else {
    alert('Ошибка: ' + data.detail);
  }
}

// Проверка кода
async function verifyCode() {
  const code = document.getElementById('code').value;
  const codeId = document.getElementById('code-id').value;
  
  // ⚠️ ВАЖНО: Этот запрос должен делать бэкенд!
  const response = await fetch('/api/verify-code', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      code_id: codeId,
      code: code
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    localStorage.setItem('accessToken', data.access_token);
    localStorage.setItem('refreshToken', data.refresh_token);
    window.location.href = '/dashboard';
  } else {
    alert('Неверный код: ' + data.detail);
  }
}

// Backend endpoint для verify (Node.js)
app.post('/api/verify-code', async (req, res) => {
  const { code_id, code } = req.body;
  
  const response = await fetch('http://localhost:8000/sso/code/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET, // Только на бэкенде!
      code_id: code_id,
      code: code
    })
  });
  
  const data = await response.json();
  res.json(data);
});
```

---

## React Component (Authorization Code Flow)

```jsx
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

function LoginPage() {
  const [searchParams] = useSearchParams();
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  
  useEffect(() => {
    if (code && state) {
      // Проверка state
      const savedState = sessionStorage.getItem('oauth_state');
      if (state !== savedState) {
        alert('Invalid state parameter');
        return;
      }
      
      // Обмен code на токены (делайте на бэкенде!)
      exchangeCodeForTokens(code);
    }
  }, [code, state]);
  
  const handleLogin = () => {
    const state = Math.random().toString(36).substring(7);
    sessionStorage.setItem('oauth_state', state);
    
    const params = new URLSearchParams({
      client_id: 'your_client_id',
      redirect_uri: 'http://localhost:3001/callback',
      state: state,
      scope: 'openid profile email'
    });
    
    window.location.href = `http://localhost:8000/sso/authorize?${params}`;
  };
  
  const exchangeCodeForTokens = async (code) => {
    try {
      const response = await fetch('/api/auth/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code })
      });
      
      const tokens = await response.json();
      localStorage.setItem('accessToken', tokens.access_token);
      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Token exchange error:', error);
    }
  };
  
  return (
    <div>
      <h1>Login</h1>
      <button onClick={handleLogin}>Login with Life SSO</button>
    </div>
  );
}

export default LoginPage;
```

---

## Vue.js Component (QR Code Flow)

```vue
<template>
  <div class="qr-login">
    <canvas id="qr-canvas"></canvas>
    <p>User Code: <strong>{{ userCode }}</strong></p>
    <p v-if="status === 'pending'">Ожидание авторизации...</p>
    <p v-if="status === 'authorized'">Авторизация успешна!</p>
  </div>
</template>

<script>
import QRCode from 'qrcode';

export default {
  data() {
    return {
      deviceCode: null,
      userCode: null,
      status: 'pending'
    };
  },
  mounted() {
    this.initiateQR();
  },
  methods: {
    async initiateQR() {
      const response = await fetch('http://localhost:8000/sso/qr/initiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: 'your_client_id',
          scope: 'openid profile email'
        })
      });
      
      const data = await response.json();
      this.deviceCode = data.device_code;
      this.userCode = data.user_code;
      
      // Генерируем QR код
      QRCode.toCanvas(document.getElementById('qr-canvas'), data.verification_uri_complete);
      
      // Начинаем polling
      this.pollStatus();
    },
    async pollStatus() {
      const maxAttempts = 120;
      let attempts = 0;
      
      const poll = async () => {
        attempts++;
        
        if (attempts > maxAttempts) {
          alert('QR-код истек');
          return;
        }
        
        try {
          const response = await fetch('http://localhost:8000/sso/qr/token', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              device_code: this.deviceCode,
              client_id: 'your_client_id',
              client_secret: 'your_client_secret' // Только на бэкенде!
            })
          });
          
          const data = await response.json();
          
          if (data.status === 'authorized') {
            this.status = 'authorized';
            localStorage.setItem('accessToken', data.access_token);
            this.$router.push('/dashboard');
          } else if (data.status === 'pending') {
            setTimeout(poll, 5000);
          }
        } catch (error) {
          console.error('Polling error:', error);
          setTimeout(poll, 5000);
        }
      };
      
      poll();
    }
  }
};
</script>
```

---

## .env файл

```env
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
REDIRECT_URI=http://localhost:3001/callback
SSO_BASE_URL=http://localhost:8000
```

---

## Заметки по безопасности

1. **НИКОГДА** не храните `client_secret` в клиентском коде
2. Все запросы с `client_secret` должны выполняться на бэкенде
3. Используйте HTTPS в продакшене
4. Проверяйте `state` параметр для защиты от CSRF
5. Храните токены безопасно (httpOnly cookies, secure storage)

---

**Версия:** 1.0  
**Дата:** 2025-01-01


