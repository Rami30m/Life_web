# 📚 Документация фронтенда Life SSO

## Оглавление
1. [Обзор архитектуры](#1-обзор-архитектуры)
2. [Структура проекта](#2-структура-проекта)
3. [Управление состоянием](#3-управление-состоянием)
4. [Компоненты](#4-компоненты)
5. [Утилиты (faceApi.js)](#5-утилиты-faceapijs)
6. [Потоки данных](#6-потоки-данных)
7. [API интеграция](#7-api-интеграция)
8. [localStorage](#8-localstorage)
9. [Безопасность](#9-безопасность)
10. [UI/UX особенности](#10-uiux-особенности)

---

## 1. Обзор архитектуры

### Основные технологии

- **Next.js 15.5.6** - React фреймворк с server/client компонентами
- **React 19.1.0** - UI библиотека
- **Tailwind CSS 4** - Utility-first CSS фреймворк
- **face-api.js 0.22.2** - Библиотека для распознавания лиц
- **react-webcam 7.2.0** - Компонент для доступа к камере

### Архитектурные принципы

1. **Client-Side Only** - Все компоненты используют `"use client"` директиву
2. **Централизованное управление состоянием** - Главный state в `page.js`
3. **Props drilling** - Данные передаются через props (без Redux/Context)
4. **localStorage синхронизация** - Персистентность данных пользователя
5. **Dynamic imports** - Ленивая загрузка тяжелых компонентов (биометрия)

### Принципы организации кода

```
life/
├── app/
│   ├── components/         # React компоненты
│   │   ├── register.js    # Регистрация
│   │   ├── login.js       # Вход
│   │   ├── main.js        # Главная страница
│   │   ├── BiometricVerification.js  # Регистрация биометрии
│   │   └── BiometricLogin.js         # Вход по лицу
│   ├── utils/             # Утилиты
│   │   └── faceApi.js    # Face-API утилиты
│   ├── page.js           # Корневой компонент (роутинг)
│   ├── layout.js         # Layout
│   └── globals.css       # Глобальные стили
├── public/
│   └── models/           # Face-API модели (7 файлов)
└── package.json
```

---

## 2. Структура проекта

### Файлы и их назначение

| Файл | Назначение | Размер/Важность |
|------|-----------|-----------------|
| `app/page.js` | Корневой компонент, роутинг, управление аутентификацией | 🔴 Критично |
| `app/components/register.js` | Форма регистрации пользователя | 🟡 Важно |
| `app/components/login.js` | Форма входа (пароль + биометрия) | 🟡 Важно |
| `app/components/main.js` | Главная страница после входа | 🟡 Важно |
| `app/components/BiometricVerification.js` | Регистрация биометрических данных | 🟠 Средне |
| `app/components/BiometricLogin.js` | Вход через распознавание лица | 🟠 Средне |
| `app/utils/faceApi.js` | Утилиты для работы с face-api.js | 🔴 Критично |
| `public/models/` | Предобученные модели нейросетей | 🔴 Критично (5+ MB) |

### Зависимости (package.json)

```json
{
  "dependencies": {
    "face-api.js": "^0.22.2",      // Распознавание лиц
    "next": "15.5.6",              // React фреймворк
    "react": "19.1.0",             // UI библиотека
    "react-dom": "19.1.0",         // React DOM
    "react-webcam": "^7.2.0"       // Доступ к камере
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4",  // Tailwind CSS
    "tailwindcss": "^4"            // Утилиты стилей
  }
}
```

---

## 3. Управление состоянием

### 3.1 Корневой state (page.js)

**Главный контейнер состояния** - все критичные данные хранятся здесь:

```javascript
const [isLogin, setIsLogin] = useState(false);           // Переключатель вход/регистрация
const [isAuthenticated, setIsAuthenticated] = useState(false);  // Статус аутентификации
const [userData, setUserData] = useState(null);          // Данные пользователя
const [accessToken, setAccessToken] = useState(null);    // JWT access токен
const [refreshToken, setRefreshToken] = useState(null);  // JWT refresh токен
```

**Инициализация из localStorage:**

```javascript
useEffect(() => {
  if (typeof window !== 'undefined') {
    const savedAccessToken = localStorage.getItem('accessToken');
    const savedRefreshToken = localStorage.getItem('refreshToken');
    const savedUserData = localStorage.getItem('userData');
    
    if (savedAccessToken && savedRefreshToken && savedUserData) {
      setAccessToken(savedAccessToken);
      setRefreshToken(savedRefreshToken);
      setUserData(JSON.parse(savedUserData));
      setIsAuthenticated(true);
    }
  }
}, []);
```

**Зачем `typeof window !== 'undefined'`?**
- Next.js использует SSR (Server-Side Rendering)
- На сервере нет `window` и `localStorage`
- Проверка предотвращает ошибки при рендеринге на сервере

### 3.2 useState в компонентах

#### register.js и login.js

```javascript
// Данные формы
const [formData, setFormData] = useState({
  email: "",
  password: "",
  // ... другие поля
});

// Статус операции (success/error)
const [status, setStatus] = useState(null);

// Индикатор загрузки
const [loading, setLoading] = useState(false);
```

**Обновление formData:**

```javascript
const handleChange = (e) => {
  setFormData({ 
    ...formData,                  // Копируем старое состояние
    [e.target.name]: e.target.value  // Обновляем конкретное поле
  });
};
```

**Почему spread operator (`...`)?**
- React не мутирует state напрямую
- Нужно создать **новый объект** для триггера ре-рендера
- `...formData` копирует все существующие поля
- `[e.target.name]` перезаписывает изменённое поле

#### BiometricVerification.js и BiometricLogin.js

```javascript
const [isModelsLoaded, setIsModelsLoaded] = useState(false);     // Загружены ли модели
const [isCapturing, setIsCapturing] = useState(false);           // Идёт ли захват
const [faceDetected, setFaceDetected] = useState(false);         // Найдено ли лицо
const [orientationStatus, setOrientationStatus] = useState({     // Ориентация головы
  isLookingStraight: false, 
  message: ''
});
const [countdown, setCountdown] = useState(null);                // Обратный отсчёт (3-2-1)
const [loading, setLoading] = useState(false);                   // Загрузка
const [status, setStatus] = useState({ type: null, message: "" }); // Статус
```

### 3.3 useEffect хуки

#### Загрузка моделей при монтировании

```javascript
useEffect(() => {
  const initializeModels = async () => {
    setStatus({ type: "info", message: "Загрузка моделей..." });
    const loaded = await loadModels();  // Асинхронная загрузка
    
    if (loaded) {
      setIsModelsLoaded(true);
      setStatus({ type: "success", message: "Готово!" });
    } else {
      setStatus({ type: "error", message: "Ошибка загрузки" });
    }
  };

  initializeModels();
  
  // Cleanup при размонтировании
  return () => {
    if (stableDetectionTimerRef.current) {
      clearTimeout(stableDetectionTimerRef.current);
    }
  };
}, []); // Пустой массив зависимостей = выполнится 1 раз при монтировании
```

**Почему cleanup функция?**
- При размонтировании компонента нужно очистить таймеры
- Без очистки = утечка памяти (memory leak)
- `return () => {}` вызывается перед размонтированием

#### Детекция лица в реальном времени

```javascript
useEffect(() => {
  if (!isModelsLoaded || isCapturing || loading) return;

  const detectInterval = setInterval(async () => {
    if (webcamRef.current && canvasRef.current) {
      const video = webcamRef.current.video;
      if (video && video.readyState === 4) {  // HAVE_ENOUGH_DATA
        const detection = await detectFace(video);
        
        if (detection) {
          drawFaceBox(canvasRef.current, video, detection);
          setFaceDetected(true);
          
          const orientation = checkFaceOrientation(detection);
          setOrientationStatus(orientation);
          
          // Запуск автоотправки при правильной ориентации
          if (orientation.isLookingStraight && !countdown) {
            startCountdown(detection);
          }
        } else {
          // Лицо не найдено - сброс
          const ctx = canvasRef.current.getContext('2d');
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
          setFaceDetected(false);
          resetCountdown();
        }
      }
    }
  }, 300); // Детекция каждые 300мс

  return () => clearInterval(detectInterval); // Очистка интервала
}, [isModelsLoaded, isCapturing, loading, countdown]);
```

**Массив зависимостей:**
- `[isModelsLoaded, isCapturing, loading, countdown]`
- useEffect перезапускается при изменении любой из этих переменных
- Если `isCapturing = true` → детекция останавливается (return early)

**Почему 300мс, а не быстрее?**
- Face-API.js тяжёлый (~50-100мс на детекцию)
- 300мс = ~3 FPS (достаточно для UI)
- Меньший интервал = больше нагрузка на CPU

### 3.4 useRef хуки

```javascript
const webcamRef = useRef(null);              // Ссылка на <Webcam>
const canvasRef = useRef(null);              // Ссылка на <canvas>
const stableDetectionTimerRef = useRef(null); // Таймер стабильной детекции
const countdownIntervalRef = useRef(null);    // Интервал обратного отсчёта
```

**Почему useRef, а не useState?**

```javascript
// ❌ ПЛОХО (useState)
const [timer, setTimer] = useState(null);
setTimeout(() => setTimer(...), 1000);  // Вызовет ре-рендер!

// ✅ ХОРОШО (useRef)
const timerRef = useRef(null);
timerRef.current = setTimeout(...);  // Не вызывает ре-рендер
```

- **useRef** - хранит значение БЕЗ ре-рендера
- **useState** - хранит значение С ре-рендером
- Для таймеров, DOM ссылок → useRef
- Для UI данных → useState

**Доступ к DOM через ref:**

```javascript
const video = webcamRef.current.video;  // Получаем <video> элемент
const ctx = canvasRef.current.getContext('2d');  // Canvas 2D контекст
```

### 3.5 Fetch запросы (API интеграция)

#### Регистрация пользователя

```javascript
const handleSubmit = async (e) => {
  e.preventDefault();  // Предотвращаем перезагрузку страницы
  setLoading(true);
  setStatus(null);

  try {
    // POST запрос на бэкенд
    const response = await fetch('http://localhost:8000/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        full_name: formData.fullName,
        email: formData.email,
        phone: formData.phone,
        birth_date: formData.birthDate,
        password: formData.password
      })
    });

    const data = await response.json();  // Парсим JSON ответ

    // Проверка статуса ответа
    if (!response.ok) {
      throw new Error(data.detail || 'Ошибка при регистрации');
    }

    // Проверка наличия токенов
    if (!data.access_token || !data.refresh_token) {
      throw new Error('Не получены токены авторизации');
    }

    // Успех - вызываем callback
    onSuccess(
      data.user,
      {
        access_token: data.access_token,
        refresh_token: data.refresh_token
      }
    );

  } catch (err) {
    // Обработка ошибки
    setStatus({ 
      type: "error", 
      message: err.message || "Ошибка при регистрации" 
    });
  } finally {
    setLoading(false);  // Всегда выключаем loading
  }
};
```

**Структура try-catch-finally:**
- `try` - основная логика
- `catch` - обработка ошибок (сеть, сервер, валидация)
- `finally` - выполняется ВСЕГДА (даже при ошибке)

#### Регистрация биометрии (с токеном)

```javascript
const response = await fetch('http://localhost:8000/biometric/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`  // ← JWT токен!
  },
  body: formatDescriptorForServer(detection.descriptor)
});
```

**Почему Authorization header?**
- Бэкенд проверяет токен → получает `current_user`
- Без токена → 401 Unauthorized
- Формат: `Bearer <token>` (стандарт OAuth 2.0)

#### Вход по биометрии (без токена)

```javascript
const response = await fetch('http://localhost:8000/biometric/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    // ← НЕТ Authorization (пользователь ещё не аутентифицирован)
  },
  body: formatDescriptorForServer(detection.descriptor)
});
```

**Почему без токена?**
- Пользователь **не залогинен** → нет токена
- Бэкенд сравнивает дескриптор со ВСЕМИ пользователями
- Возвращает токены при успешном распознавании

### 3.6 Передача данных через props

#### Иерархия компонентов

```
page.js (корень)
  ├── userData, accessToken, refreshToken (state)
  ├── handleSuccessfulAuth()
  ├── handleUserUpdate()
  └── handleLogout()
      │
      ├─→ MainPage
      │     props: userData, accessToken, onLogout, onUserUpdate
      │     │
      │     └─→ BiometricVerification
      │           props: accessToken, onSuccess, onCancel
      │
      ├─→ LoginPage
      │     props: onSwitch, onSuccess
      │     │
      │     └─→ BiometricLogin
      │           props: onSuccess, onCancel
      │
      └─→ RegisterPage
            props: onSwitch, onSuccess
```

**Пример передачи:**

```javascript
// page.js
<MainPage 
  userData={userData}              // Данные пользователя
  accessToken={accessToken}        // JWT токен
  onLogout={handleLogout}          // Функция выхода
  onUserUpdate={handleUserUpdate}  // Функция обновления данных
/>

// main.js
export default function MainPage({ userData, accessToken, onLogout, onUserUpdate }) {
  // ...
  <BiometricVerification 
    accessToken={accessToken}      // Передаём токен дальше
    onSuccess={handleBiometricSuccess}  // Свой callback
    onCancel={() => setShowBiometric(false)}
  />
}
```

**Callbacks (функции обратного вызова):**

```javascript
// Ребёнок вызывает функцию родителя
const handleBiometricSuccess = (updatedUser) => {
  setBiometricVerified(true);
  setShowBiometric(false);
  
  // Передаём данные ВВЕРХ к page.js
  if (updatedUser && onUserUpdate) {
    onUserUpdate(updatedUser);
  }
};
```

**Поток данных:**
```
BiometricVerification → onSuccess(data.user)
  ↓
MainPage → handleBiometricSuccess(updatedUser)
  ↓
MainPage → onUserUpdate(updatedUser)
  ↓
page.js → handleUserUpdate(updatedUser)
  ↓
  ├─ setUserData(updatedUser)
  └─ localStorage.setItem('userData', ...)
```

---

## 4. Компоненты

### 4.1 page.js - Корневой компонент

**Назначение:**
- Управление роутингом (вход/регистрация/главная)
- Хранение глобального state (токены, userData)
- Синхронизация с localStorage
- Обработка аутентификации

**Основные функции:**

#### handleSuccessfulAuth()

```javascript
const handleSuccessfulAuth = (user, tokens) => {
  // Обновляем state
  setUserData(user);
  setAccessToken(tokens.access_token);
  setRefreshToken(tokens.refresh_token);
  setIsAuthenticated(true);
  
  // Сохраняем в localStorage
  if (typeof window !== 'undefined') {
    localStorage.setItem('accessToken', tokens.access_token);
    localStorage.setItem('refreshToken', tokens.refresh_token);
    localStorage.setItem('userData', JSON.stringify(user));
  }
};
```

**Когда вызывается:**
- После успешной регистрации
- После успешного входа (пароль или биометрия)

**Что делает:**
1. Обновляет state (4 переменные)
2. Сохраняет в localStorage (3 ключа)
3. `setIsAuthenticated(true)` → переключает на MainPage

#### handleUserUpdate()

```javascript
const handleUserUpdate = (updatedUser) => {
  setUserData(updatedUser);  // Обновляем state
  
  if (typeof window !== 'undefined') {
    localStorage.setItem('userData', JSON.stringify(updatedUser));
  }
};
```

**Когда вызывается:**
- После успешной биометрической верификации
- Когда `is_biometric_verified` изменяется с `false` → `true`

**Зачем нужен:**
- Бэкенд обновляет флаг в БД
- Нужно обновить фронтенд БЕЗ повторного логина
- Обновляется только userData (токены остаются)

#### handleLogout()

```javascript
const handleLogout = async () => {
  // Отзываем refresh токен на сервере
  if (refreshToken) {
    try {
      await fetch('http://localhost:8000/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    } catch (error) {
      console.error('Ошибка при выходе:', error);
    }
  }

  // Очищаем state
  setIsAuthenticated(false);
  setUserData(null);
  setAccessToken(null);
  setRefreshToken(null);
  
  // Очищаем localStorage
  if (typeof window !== 'undefined') {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('userData');
  }
};
```

**Последовательность:**
1. Отправляем запрос `/logout` (отзыв refresh токена в БД)
2. Очищаем state (4 переменные)
3. Очищаем localStorage (3 ключа)
4. React автоматически переключает на RegisterPage (из-за `isAuthenticated = false`)

**Почему не ждём ответа сервера?**
- Используем `try-catch` без `await` в начале
- Даже если сервер недоступен, локальный выход произойдёт
- UX важнее - пользователь сразу видит форму входа

#### Условный рендеринг

```javascript
return (
  <div>
    {isAuthenticated ? (
      <MainPage {...props} />
    ) : isLogin ? (
      <LoginPage {...props} />
    ) : (
      <RegisterPage {...props} />
    )}
  </div>
);
```

**Логика:**
```
isAuthenticated === true  → MainPage
isAuthenticated === false И isLogin === true  → LoginPage
isAuthenticated === false И isLogin === false → RegisterPage
```

---

### 4.2 register.js - Регистрация

**Назначение:**
- Форма регистрации нового пользователя
- Валидация полей
- Отправка данных на бэкенд
- Получение JWT токенов

**State:**

```javascript
const [formData, setFormData] = useState({
  fullName: "",
  email: "",
  phone: "",
  birthDate: "",
  password: "",
  confirmPassword: ""
});

const [status, setStatus] = useState(null);  // { type: "success" | "error", message: string }
const [loading, setLoading] = useState(false);
```

**Валидация (клиентская):**

```javascript
const handleChange = (e) => {
  setFormData({ ...formData, [e.target.name]: e.target.value });
};
```

**HTML5 валидация:**
```jsx
<input
  type="email"     // Проверка формата email
  required         // Обязательное поле
  minLength={8}    // Минимальная длина пароля
  pattern="^\+7\d{10}$"  // Телефон: +7XXXXXXXXXX
/>
```

**Отправка формы:**

```javascript
const handleSubmit = async (e) => {
  e.preventDefault();
  
  // Проверка паролей
  if (formData.password !== formData.confirmPassword) {
    setStatus({ type: "error", message: "Пароли не совпадают" });
    return;
  }

  setLoading(true);
  setStatus(null);

  try {
    const response = await fetch('http://localhost:8000/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: formData.fullName,
        email: formData.email,
        phone: formData.phone,
        birth_date: formData.birthDate,
        password: formData.password
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Ошибка при регистрации');
    }

    if (!data.access_token || !data.refresh_token) {
      throw new Error('Не получены токены авторизации');
    }

    // Успех - вызываем callback родителя
    onSuccess(data.user, {
      access_token: data.access_token,
      refresh_token: data.refresh_token
    });

  } catch (err) {
    setStatus({ 
      type: "error", 
      message: err.message || "Ошибка при регистрации" 
    });
  } finally {
    setLoading(false);
  }
};
```

**UI состояния:**

```jsx
{/* Форма - показывается только если НЕ loading и НЕТ status */}
{!status && !loading && (
  <form onSubmit={handleSubmit}>
    {/* ... поля формы ... */}
  </form>
)}

{/* Индикатор загрузки */}
{loading && (
  <div className="flex justify-center">
    <div className="animate-bounce">Загрузка...</div>
  </div>
)}

{/* Сообщение об успехе/ошибке */}
{status && !loading && (
  <div className={status.type === "success" ? "bg-green-100" : "bg-red-100"}>
    {status.message}
  </div>
)}
```

**Переключение на вход:**

```jsx
<button type="button" onClick={onSwitch}>
  Уже есть аккаунт? Войти
</button>
```

`onSwitch` → вызывает `setIsLogin(true)` в `page.js` → показывает LoginPage

---

### 4.3 login.js - Вход

**Назначение:**
- Вход по email + пароль
- Вход по биометрии (кнопка)
- Отправка данных на бэкенд
- Получение JWT токенов

**State:**

```javascript
const [formData, setFormData] = useState({
  email: "",
  password: ""
});

const [status, setStatus] = useState(null);
const [loading, setLoading] = useState(false);
const [showBiometricLogin, setShowBiometricLogin] = useState(false);
```

**Вход по паролю:**

```javascript
const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);
  setStatus(null);

  try {
    const response = await fetch('http://localhost:8000/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: formData.email,
        password: formData.password
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Неверный email или пароль');
    }

    if (!data.access_token || !data.refresh_token) {
      throw new Error('Не получены токены авторизации');
    }

    // Успех - переходим на главную
    onSuccess(data.user, {
      access_token: data.access_token,
      refresh_token: data.refresh_token
    });

  } catch (err) {
    setStatus({ 
      type: "error", 
      message: err.message || "Ошибка при входе" 
    });
  } finally {
    setLoading(false);
  }
};
```

**Переключение на биометрический вход:**

```jsx
{/* Если showBiometricLogin = true → показываем BiometricLogin */}
if (showBiometricLogin) {
  return (
    <BiometricLogin
      onSuccess={onSuccess}  // Передаём callback от page.js
      onCancel={() => setShowBiometricLogin(false)}
    />
  );
}

{/* Иначе показываем форму входа */}
return (
  <div>
    <form onSubmit={handleSubmit}>
      {/* Email и пароль */}
    </form>
    
    {/* Разделитель */}
    <div className="my-6">или</div>
    
    {/* Кнопка входа по лицу */}
    <button onClick={() => setShowBiometricLogin(true)}>
      Войти по лицу
    </button>
  </div>
);
```

**Логика:**
- По умолчанию `showBiometricLogin = false` → форма
- Нажатие "Войти по лицу" → `setShowBiometricLogin(true)` → BiometricLogin
- "Отмена" в BiometricLogin → `setShowBiometricLogin(false)` → форма

---

### 4.4 main.js - Главная страница

**Назначение:**
- Приветствие пользователя
- Показ статуса верификации
- Кнопки функционала (цифровое удостоверение, биометрия)
- Выход из аккаунта

**State:**

```javascript
const [showCard, setShowCard] = useState(false);           // Показать удостоверение
const [showBiometric, setShowBiometric] = useState(false); // Показать компонент биометрии
const [biometricVerified, setBiometricVerified] = useState(false); // Локальный флаг
```

**Props:**

```javascript
export default function MainPage({ 
  userData,       // Данные пользователя
  accessToken,    // JWT токен
  onLogout,       // Callback выхода
  onUserUpdate    // Callback обновления данных
})
```

**Статус верификации:**

```jsx
{userData?.is_biometric_verified ? (
  <div className="bg-green-100 text-green-700">
    <svg>✓</svg>
    <span>Аккаунт верифицирован</span>
  </div>
) : (
  <div className="bg-orange-100 text-orange-700">
    <svg>⚠</svg>
    <span>Требуется верификация</span>
  </div>
)}
```

**Обработка успешной верификации:**

```javascript
const handleBiometricSuccess = (updatedUser) => {
  setBiometricVerified(true);  // Локальный флаг (для UI)
  setShowBiometric(false);     // Закрываем компонент биометрии
  
  // Обновляем userData в page.js
  if (updatedUser && onUserUpdate) {
    onUserUpdate(updatedUser);  // → page.js → handleUserUpdate
  }
};
```

**Поток данных при верификации:**

```
1. BiometricVerification → onSuccess(data.user)
   ↓
2. main.js → handleBiometricSuccess(updatedUser)
   ↓
3. main.js → onUserUpdate(updatedUser)
   ↓
4. page.js → handleUserUpdate(updatedUser)
   ↓
5. page.js → setUserData(updatedUser)
   ↓ (userData изменился)
6. main.js → ре-рендер с новым userData
   ↓
7. userData.is_biometric_verified = true
   ↓
8. UI показывает "Аккаунт верифицирован" ✅
```

**Переключение на биометрию:**

```jsx
{showBiometric ? (
  <BiometricVerification 
    accessToken={accessToken}
    onSuccess={handleBiometricSuccess}
    onCancel={() => setShowBiometric(false)}
  />
) : (
  // Главная страница
  <div>
    {/* ... контент ... */}
    <button onClick={() => setShowBiometric(true)}>
      Верификация биометрией
    </button>
  </div>
)}
```

---

### 4.5 BiometricVerification.js - Регистрация биометрии

**Назначение:**
- Доступ к камере пользователя
- Загрузка моделей face-api.js
- Детекция лица в реальном времени
- Проверка ориентации головы
- Автоматическая отправка после 3 секунд
- Отправка дескрипторов на бэкенд

**State:**

```javascript
const [isModelsLoaded, setIsModelsLoaded] = useState(false);
const [isCapturing, setIsCapturing] = useState(false);
const [status, setStatus] = useState({ type: null, message: "" });
const [faceDetected, setFaceDetected] = useState(false);
const [orientationStatus, setOrientationStatus] = useState({ 
  isLookingStraight: false, 
  message: '' 
});
const [countdown, setCountdown] = useState(null);  // 3, 2, 1, null
const [loading, setLoading] = useState(false);
```

**Refs:**

```javascript
const webcamRef = useRef(null);              // <Webcam> элемент
const canvasRef = useRef(null);              // <canvas> для рисования рамки
const stableDetectionTimerRef = useRef(null); // Таймер стабильной детекции
const countdownIntervalRef = useRef(null);    // Интервал обратного отсчёта
```

**Загрузка моделей:**

```javascript
useEffect(() => {
  const initializeModels = async () => {
    setStatus({ type: "info", message: "Загрузка моделей..." });
    const loaded = await loadModels();  // Из utils/faceApi.js
    
    if (loaded) {
      setIsModelsLoaded(true);
      setStatus({ type: "success", message: "Готово! Посмотрите прямо в камеру" });
    } else {
      setStatus({ type: "error", message: "Ошибка загрузки моделей" });
    }
  };

  initializeModels();
  
  // Cleanup
  return () => {
    if (stableDetectionTimerRef.current) {
      clearTimeout(stableDetectionTimerRef.current);
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }
  };
}, []);
```

**Детекция лица (каждые 300мс):**

```javascript
useEffect(() => {
  if (!isModelsLoaded || isCapturing || loading) return;

  const detectInterval = setInterval(async () => {
    if (webcamRef.current && canvasRef.current) {
      const video = webcamRef.current.video;
      
      if (video && video.readyState === 4) {  // Видео готово
        const detection = await detectFace(video);
        
        if (detection) {
          // Рисуем зелёную рамку и точки
          drawFaceBox(canvasRef.current, video, detection);
          setFaceDetected(true);
          
          // Проверяем ориентацию
          const orientation = checkFaceOrientation(detection);
          setOrientationStatus(orientation);
          
          // Если лицо прямо → запускаем обратный отсчёт
          if (orientation.isLookingStraight) {
            if (!stableDetectionTimerRef.current && !countdown) {
              startCountdown(detection);
            }
          } else {
            resetCountdown();  // Лицо отвернулось → сброс
          }
        } else {
          // Лицо не найдено
          const ctx = canvasRef.current.getContext('2d');
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
          setFaceDetected(false);
          setOrientationStatus({ isLookingStraight: false, message: 'Лицо не обнаружено' });
          resetCountdown();
        }
      }
    }
  }, 300);

  return () => clearInterval(detectInterval);
}, [isModelsLoaded, isCapturing, loading, countdown]);
```

**Обратный отсчёт (3-2-1):**

```javascript
const startCountdown = (detection) => {
  let count = 3;
  setCountdown(count);
  
  countdownIntervalRef.current = setInterval(() => {
    count--;
    setCountdown(count);
    
    if (count <= 0) {
      clearInterval(countdownIntervalRef.current);
      handleAutoCapture(detection);  // Автоотправка!
    }
  }, 1000);  // Каждую секунду
};

const resetCountdown = () => {
  if (stableDetectionTimerRef.current) {
    clearTimeout(stableDetectionTimerRef.current);
    stableDetectionTimerRef.current = null;
  }
  if (countdownIntervalRef.current) {
    clearInterval(countdownIntervalRef.current);
    countdownIntervalRef.current = null;
  }
  setCountdown(null);
};
```

**Логика обратного отсчёта:**
```
Лицо прямо → startCountdown(3)
  ↓ 1 секунда
countdown = 2
  ↓ 1 секунда
countdown = 1
  ↓ 1 секунда
countdown = 0
  ↓
handleAutoCapture() → отправка!

Если лицо отвернулось → resetCountdown() → countdown = null
```

**Автоматический захват и отправка:**

```javascript
const handleAutoCapture = async (initialDetection) => {
  if (!webcamRef.current || isCapturing) return;

  setIsCapturing(true);
  setLoading(true);
  setCountdown(null);
  setStatus({ type: "info", message: "Сохранение биометрии..." });

  try {
    const video = webcamRef.current.video;
    const detection = await detectFace(video);

    // Валидация качества
    const validation = validateFaceQuality(detection);
    if (!validation.valid) {
      setStatus({ type: "error", message: validation.message });
      setIsCapturing(false);
      setLoading(false);
      return;
    }

    // Проверяем ориентацию ещё раз
    const orientation = checkFaceOrientation(detection);
    if (!orientation.isLookingStraight) {
      setStatus({ type: "error", message: "Пожалуйста, смотрите прямо в камеру" });
      setIsCapturing(false);
      setLoading(false);
      return;
    }

    // Отправка на бэкенд
    const response = await fetch('http://localhost:8000/biometric/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`  // ← Требуется токен!
      },
      body: formatDescriptorForServer(detection.descriptor)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Ошибка при сохранении биометрии');
    }

    // Успех! Передаём обновлённого пользователя
    setStatus({ type: "success", message: "Биометрия успешно зарегистрирована!" });
    
    setTimeout(() => {
      onSuccess(data.user);  // ← Важно! Передаём data.user
    }, 1500);

  } catch (err) {
    setStatus({ type: "error", message: err.message || 'Ошибка при регистрации' });
    setIsCapturing(false);
    setLoading(false);
  }
};
```

**Ключевые моменты:**
1. **Двойная проверка** - качество + ориентация перед отправкой
2. **Authorization header** - требуется JWT токен
3. **Передача data.user** - обновлённые данные пользователя с `is_biometric_verified = true`

**UI:**

```jsx
<div className="relative">
  {/* Обратный отсчёт поверх камеры */}
  {countdown !== null && countdown > 0 && (
    <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
      <div className="text-white text-8xl font-bold animate-pulse">
        {countdown}
      </div>
    </div>
  )}
  
  {/* Webcam */}
  <Webcam
    audio={false}
    ref={webcamRef}
    screenshotFormat="image/jpeg"
    width={320}
    height={240}
    videoConstraints={{ facingMode: "user" }}
  />
  
  {/* Canvas поверх видео */}
  <canvas ref={canvasRef} className="absolute top-0 left-0" />
</div>

{/* Статус ориентации */}
{faceDetected ? (
  <div className={orientationStatus.isLookingStraight ? 'text-green-600' : 'text-orange-600'}>
    {orientationStatus.message}
  </div>
) : (
  <div className="text-red-600">
    Лицо не обнаружено
  </div>
)}
```

---

### 4.6 BiometricLogin.js - Вход по лицу

**Назначение:**
- Вход в систему через распознавание лица
- Аналогичен BiometricVerification, но:
  - НЕ требует токена
  - Отправляет на `/biometric/login`
  - Возвращает токены (как обычный вход)

**Отличия от BiometricVerification:**

```javascript
// BiometricVerification (регистрация)
const response = await fetch('http://localhost:8000/biometric/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`  // ← Есть токен
  },
  body: formatDescriptorForServer(detection.descriptor)
});

// BiometricLogin (вход)
const response = await fetch('http://localhost:8000/biometric/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    // ← НЕТ токена (пользователь не залогинен)
  },
  body: formatDescriptorForServer(detection.descriptor)
});
```

**Обработка ответа:**

```javascript
const data = await response.json();

if (!response.ok) {
  throw new Error(data.detail || 'Лицо не распознано');
}

// Бэкенд вернул токены (как при обычном входе)
setStatus({ type: "success", message: "Вход выполнен успешно!" });

setTimeout(() => {
  onSuccess(data.user, {
    access_token: data.access_token,
    refresh_token: data.refresh_token
  });
}, 1000);
```

**Вызов onSuccess:**
- `onSuccess` → `handleSuccessfulAuth` в `page.js`
- Сохраняет токены и userData
- `setIsAuthenticated(true)` → переход на MainPage

---

## 5. Утилиты (faceApi.js)

**Назначение:**
- Обёртки над face-api.js
- Упрощение работы с моделями
- Валидация детекции
- Проверка ориентации лица

### 5.1 loadModels()

```javascript
import * as faceapi from 'face-api.js';

let modelsLoaded = false;  // Глобальный флаг

export const loadModels = async () => {
  if (modelsLoaded) {
    console.log('✅ Модели уже загружены');
    return true;
  }

  try {
    console.log('📦 Загрузка моделей face-api.js...');
    
    const MODEL_URL = '/models';  // public/models/
    
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]);

    modelsLoaded = true;
    console.log('✅ Модели успешно загружены');
    return true;
  } catch (error) {
    console.error('❌ Ошибка загрузки моделей:', error);
    return false;
  }
};
```

**Модели:**
1. **tinyFaceDetector** - быстрая детекция лица (~5MB)
2. **faceLandmark68Net** - 68 точек на лице (глаза, нос, рот) (~400KB)
3. **faceRecognitionNet** - дескрипторы (128 чисел) для распознавания (~6MB)

**Почему Promise.all?**
- Параллельная загрузка (быстрее)
- Если одна ошибка → все fail
- Все модели нужны одновременно

### 5.2 detectFace()

```javascript
export const detectFace = async (video) => {
  try {
    const detection = await faceapi
      .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptor();
    
    return detection || null;
  } catch (error) {
    console.error('❌ Ошибка детекции лица:', error);
    return null;
  }
};
```

**Что возвращает:**
```javascript
detection = {
  detection: {
    box: { x, y, width, height },  // Координаты лица
    score: 0.95                     // Уверенность (0-1)
  },
  landmarks: {
    positions: [                     // 68 точек
      { x: 120, y: 150 },  // Точка 0
      { x: 122, y: 152 },  // Точка 1
      // ... 66 точек
    ]
  },
  descriptor: Float32Array(128) [   // 128 чисел для распознавания
    0.123, -0.456, 0.789, ...
  ]
}
```

**TinyFaceDetectorOptions:**
```javascript
new faceapi.TinyFaceDetectorOptions({
  inputSize: 416,        // Размер входа (больше = точнее, но медленнее)
  scoreThreshold: 0.5    // Минимальная уверенность (0-1)
})
```

### 5.3 drawFaceBox()

```javascript
export const drawFaceBox = (canvas, video, detection) => {
  if (!canvas || !detection) return;
  
  const ctx = canvas.getContext('2d');
  const box = detection.detection.box;
  
  // Очищаем canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Рисуем зелёную рамку
  ctx.strokeStyle = '#00ff00';
  ctx.lineWidth = 3;
  ctx.strokeRect(box.x, box.y, box.width, box.height);
  
  // Рисуем 68 зелёных точек (landmarks)
  if (detection.landmarks) {
    ctx.fillStyle = '#00ff00';
    detection.landmarks.positions.forEach((point) => {
      ctx.beginPath();
      ctx.arc(point.x, point.y, 2, 0, 2 * Math.PI);
      ctx.fill();
    });
  }
  
  // Показываем уверенность
  const confidence = Math.round(detection.detection.score * 100);
  ctx.fillStyle = '#00ff00';
  ctx.font = 'bold 16px Arial';
  ctx.fillText(`${confidence}%`, box.x, box.y - 10);
};
```

**Canvas поверх видео:**
```jsx
<div className="relative">
  <video ref={videoRef} />
  <canvas ref={canvasRef} className="absolute top-0 left-0" />
</div>
```

**Почему Canvas?**
- Рисование поверх видео без изменения самого видео
- Обновляется каждые 300мс (синхронно с детекцией)
- Лёгкий (не тормозит видео)

### 5.4 validateFaceQuality()

```javascript
export const validateFaceQuality = (detection) => {
  if (!detection) {
    return {
      valid: false,
      message: 'Лицо не обнаружено. Пожалуйста, посмотрите в камеру.'
    };
  }

  // Проверяем уверенность детекции
  if (detection.detection.score < 0.5) {
    return {
      valid: false,
      message: 'Качество изображения низкое. Улучшите освещение.'
    };
  }

  // Проверяем размер лица (не слишком далеко)
  const box = detection.detection.box;
  if (box.width < 100 || box.height < 100) {
    return {
      valid: false,
      message: 'Подойдите ближе к камере.'
    };
  }

  return {
    valid: true,
    message: 'Лицо успешно обнаружено!'
  };
};
```

**Проверки:**
1. **Наличие** - `detection !== null`
2. **Уверенность** - `score >= 0.5` (50%)
3. **Размер** - `width/height >= 100px`

**Зачем проверка размера?**
- Маленькое лицо = далеко от камеры
- Далеко = низкое качество дескрипторов
- Может не распознать при входе

### 5.5 checkFaceOrientation()

**Самая сложная функция!**

```javascript
export const checkFaceOrientation = (detection) => {
  if (!detection || !detection.landmarks) {
    return {
      isLookingStraight: false,
      message: 'Лицо не обнаружено',
      angles: null
    };
  }

  try {
    const landmarks = detection.landmarks.positions;
    
    // Проверяем что есть 68 точек
    if (!landmarks || landmarks.length < 68) {
      console.warn('Недостаточно landmarks точек:', landmarks?.length);
      return {
        isLookingStraight: true,  // Не блокируем если нет landmarks
        message: 'Лицо обнаружено',
        angles: null
      };
    }
    
    // Ключевые точки:
    const leftEye = landmarks[36];   // Левый глаз (внешний угол)
    const rightEye = landmarks[45];  // Правый глаз (внешний угол)
    const nose = landmarks[30];      // Кончик носа
    
    if (!leftEye || !rightEye || !nose) {
      return {
        isLookingStraight: true,
        message: 'Лицо обнаружено',
        angles: null
      };
    }
    
    // Вычисляем расстояние между глазами
    const eyeDistance = Math.sqrt(
      Math.pow(rightEye.x - leftEye.x, 2) + 
      Math.pow(rightEye.y - leftEye.y, 2)
    );
    
    // Центр между глазами
    const eyeCenter = {
      x: (leftEye.x + rightEye.x) / 2,
      y: (leftEye.y + rightEye.y) / 2
    };
    
    // === Проверка 1: Yaw (поворот влево/вправо) ===
    const horizontalOffset = Math.abs(nose.x - eyeCenter.x);
    const horizontalThreshold = eyeDistance * 0.2;  // 20% от расстояния между глазами
    
    // === Проверка 2: Pitch (наклон вверх/вниз) ===
    const verticalOffset = Math.abs(nose.y - eyeCenter.y);
    const verticalThreshold = eyeDistance * 0.4;  // 40%
    
    // === Проверка 3: Roll (наклон головы) ===
    const eyeAngle = Math.abs(
      Math.atan2(rightEye.y - leftEye.y, rightEye.x - leftEye.x) * (180 / Math.PI)
    );
    const rollThreshold = 20;  // 20 градусов
    
    // Итоговая проверка
    const isLookingStraight = 
      horizontalOffset < horizontalThreshold && 
      verticalOffset < verticalThreshold && 
      eyeAngle < rollThreshold;
    
    // Формируем сообщение
    let message = '';
    if (horizontalOffset >= horizontalThreshold) {
      message = nose.x < eyeCenter.x 
        ? 'Поверните голову немного вправо' 
        : 'Поверните голову немного влево';
    } else if (verticalOffset >= verticalThreshold) {
      message = nose.y < eyeCenter.y 
        ? 'Поднимите голову немного вверх' 
        : 'Опустите голову немного вниз';
    } else if (eyeAngle >= rollThreshold) {
      message = 'Выровняйте голову (не наклоняйте)';
    } else {
      message = 'Отлично! Держите так';
    }
    
    return {
      isLookingStraight,
      message,
      angles: {
        yaw: horizontalOffset / horizontalThreshold,    // 0-1+ (0 = идеально)
        pitch: verticalOffset / verticalThreshold,      // 0-1+ (0 = идеально)
        roll: eyeAngle / rollThreshold                  // 0-1+ (0 = идеально)
      }
    };
  } catch (error) {
    console.error('Ошибка в checkFaceOrientation:', error);
    return {
      isLookingStraight: true,  // При ошибке не блокируем
      message: 'Лицо обнаружено',
      angles: null
    };
  }
};
```

**Визуализация проверок:**

```
        leftEye (36)  eyeCenter  rightEye (45)
            •─────────────•─────────────•
                          │
                          │ (если нос здесь = ПРЯМО)
                          │
                        nose (30)
                          •
```

**Yaw (поворот влево/вправо):**
```
ПРЯМО:           ВЛЕВО:           ВПРАВО:
    👁️  👁️           👁️ 👁️             👁️  👁️
      👃              👃                  👃
  (центр)      (левее)          (правее)
```

**Pitch (наклон вверх/вниз):**
```
ВВЕРХ:           ПРЯМО:           ВНИЗ:
      👃
    👁️  👁️           👁️  👁️           👁️  👁️
                      👃                👃
```

**Roll (наклон головы):**
```
ПРЯМО:        НАКЛОН:
  👁️  👁️         👁️   👁️
    👃           👃
```

**Пороги (можно настроить):**
- **Yaw:** 20% от расстояния между глазами
- **Pitch:** 40% (мягче, т.к. нос может быть ниже)
- **Roll:** 20° (градусы наклона)

### 5.6 formatDescriptorForServer()

```javascript
export const formatDescriptorForServer = (descriptor) => {
  return JSON.stringify({
    descriptor: Array.from(descriptor),  // Float32Array → обычный массив
    timestamp: new Date().toISOString(),
    version: '1.0'
  });
};
```

**Пример:**
```javascript
// descriptor = Float32Array(128) [0.123, -0.456, ...]

formatDescriptorForServer(descriptor)
// ↓
"{
  "descriptor": [0.123, -0.456, 0.789, ...],  // 128 чисел
  "timestamp": "2025-10-29T12:34:56.789Z",
  "version": "1.0"
}"
```

**Зачем Array.from?**
- `Float32Array` не сериализуется в JSON корректно
- `Array.from` конвертирует в обычный массив
- Бэкенд получает `list[float]` в Python

---

## 6. Потоки данных

### 6.1 Регистрация пользователя

```
1. User вводит данные → formData
   ↓
2. Нажатие "Зарегистрироваться" → handleSubmit()
   ↓
3. Валидация (пароли совпадают?)
   ↓
4. fetch POST /register {full_name, email, phone, birth_date, password}
   ↓
5. Бэкенд:
   - Хеширует пароль (bcrypt)
   - Создаёт User в БД
   - Генерирует access + refresh токены (JWT)
   - Возвращает {user, access_token, refresh_token}
   ↓
6. Фронтенд: onSuccess(user, tokens)
   ↓
7. page.js → handleSuccessfulAuth()
   - setUserData(user)
   - setAccessToken(access_token)
   - setRefreshToken(refresh_token)
   - setIsAuthenticated(true)
   - localStorage.setItem('userData', user)
   - localStorage.setItem('accessToken', ...)
   - localStorage.setItem('refreshToken', ...)
   ↓
8. React ре-рендер → показывает MainPage
```

### 6.2 Вход по паролю

```
1. User вводит email + password → formData
   ↓
2. Нажатие "Войти" → handleSubmit()
   ↓
3. fetch POST /login {email, password}
   ↓
4. Бэкенд:
   - Находит User по email
   - Проверяет пароль (bcrypt.checkpw)
   - Генерирует access + refresh токены
   - Возвращает {user, access_token, refresh_token}
   ↓
5. Фронтенд: onSuccess(user, tokens)
   ↓
6. page.js → handleSuccessfulAuth()
   (аналогично регистрации)
   ↓
7. React ре-рендер → MainPage
```

### 6.3 Регистрация биометрии

```
1. MainPage: Нажатие "Верификация биометрией"
   ↓
2. setShowBiometric(true) → показываем BiometricVerification
   ↓
3. BiometricVerification:
   - Загружает модели face-api.js
   - Запускает камеру (react-webcam)
   - Детекция лица каждые 300мс
   ↓
4. Лицо найдено + смотрит прямо
   ↓
5. Запуск обратного отсчёта (3-2-1)
   ↓
6. countdown = 0 → handleAutoCapture()
   - Финальная валидация (качество + ориентация)
   - Извлекает descriptor (128 чисел)
   - fetch POST /biometric/register {descriptor, timestamp, version}
     + Authorization: Bearer <accessToken>
   ↓
7. Бэкенд:
   - Декодирует JWT → получает current_user
   - Шифрует descriptor (AES-256)
   - Сохраняет в BiometricData
   - Устанавливает is_biometric_verified = true
   - Возвращает {message, user_id, verified, user}
   ↓
8. Фронтенд: onSuccess(data.user)
   ↓
9. MainPage → handleBiometricSuccess(updatedUser)
   ↓
10. page.js → handleUserUpdate(updatedUser)
    - setUserData(updatedUser)  // is_biometric_verified = true
    - localStorage.setItem('userData', updatedUser)
   ↓
11. React ре-рендер → MainPage показывает "Аккаунт верифицирован" ✅
```

### 6.4 Вход по биометрии

```
1. LoginPage: Нажатие "Войти по лицу"
   ↓
2. setShowBiometricLogin(true) → BiometricLogin
   ↓
3. BiometricLogin:
   - Загружает модели
   - Запускает камеру
   - Детекция + ориентация
   - Обратный отсчёт
   ↓
4. handleAutoCapture()
   - Извлекает descriptor
   - fetch POST /biometric/login {descriptor, timestamp, version}
     (БЕЗ Authorization - пользователь не залогинен!)
   ↓
5. Бэкенд:
   - Получает ВСЕ BiometricData из БД
   - Расшифровывает каждый descriptor (AES-256)
   - Вычисляет евклидово расстояние с полученным
   - Находит лучшее совпадение (distance < 0.6)
   - Если найдено → генерирует токены
   - Возвращает {user, access_token, refresh_token}
   ↓
6. Фронтенд: onSuccess(user, tokens)
   ↓
7. page.js → handleSuccessfulAuth()
   (аналогично обычному входу)
   ↓
8. React ре-рендер → MainPage
```

### 6.5 Обновление userData после верификации

**Проблема:**
- После регистрации биометрии `is_biometric_verified` меняется в БД
- Но фронтенд не знает об этом (токены не меняются)
- Нужно обновить userData БЕЗ повторного логина

**Решение:**

```
1. Бэкенд: POST /biometric/register возвращает обновлённого user
   {
     message: "...",
     user: {
       id: 1,
       email: "test@example.com",
       is_biometric_verified: true  ← ОБНОВЛЕНО!
     }
   }
   ↓
2. BiometricVerification: onSuccess(data.user)
   ↓
3. MainPage: handleBiometricSuccess(updatedUser)
   ↓
4. MainPage: onUserUpdate(updatedUser)
   ↓
5. page.js: handleUserUpdate(updatedUser)
   - setUserData(updatedUser)  ← Обновляем state
   - localStorage.setItem('userData', JSON.stringify(updatedUser))  ← Обновляем localStorage
   ↓
6. React ре-рендер:
   - MainPage получает новый userData через props
   - Условный рендеринг: userData.is_biometric_verified = true
   - Показывает "Аккаунт верифицирован" ✅
```

---

## 7. API интеграция

### 7.1 Эндпоинты бэкенда

| Метод | Эндпоинт | Требует токен? | Назначение |
|-------|----------|----------------|------------|
| POST | `/register` | ❌ | Регистрация пользователя |
| POST | `/login` | ❌ | Вход по паролю |
| POST | `/refresh` | ❌ (refresh token в body) | Обновление access токена |
| POST | `/logout` | ❌ (refresh token в body) | Выход (отзыв refresh токена) |
| GET | `/me` | ✅ | Получение данных текущего пользователя |
| POST | `/biometric/register` | ✅ | Регистрация биометрии |
| POST | `/biometric/login` | ❌ | Вход по биометрии |

### 7.2 Формат запросов

#### POST /register

**Request:**
```json
{
  "full_name": "Иван Иванов",
  "email": "ivan@example.com",
  "phone": "+79991234567",
  "birth_date": "1990-01-01",
  "password": "SecurePass123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "a1b2c3d4e5f6...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "ivan@example.com",
    "full_name": "Иван Иванов",
    "phone": "+79991234567",
    "birth_date": "1990-01-01",
    "is_active": true,
    "is_biometric_verified": false,
    "created_at": "2025-10-29T12:34:56.789Z"
  }
}
```

**Response (400 - Email занят):**
```json
{
  "detail": "Email уже зарегистрирован"
}
```

#### POST /login

**Request:**
```json
{
  "email": "ivan@example.com",
  "password": "SecurePass123"
}
```

**Response (200):**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { /* userData */ }
}
```

**Response (401 - Неверный пароль):**
```json
{
  "detail": "Неверный email или пароль"
}
```

#### POST /biometric/register

**Request:**
```json
{
  "descriptor": [0.123, -0.456, 0.789, ...],  // 128 чисел
  "timestamp": "2025-10-29T12:34:56.789Z",
  "version": "1.0"
}
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200):**
```json
{
  "message": "Биометрия успешно зарегистрирована",
  "user_id": 1,
  "verified": true,
  "user": {
    "id": 1,
    "email": "ivan@example.com",
    "is_biometric_verified": true,  ← Обновлено!
    /* ... остальные поля ... */
  }
}
```

**Response (401 - Нет токена):**
```json
{
  "detail": "Не предоставлен токен авторизации"
}
```

**Response (400 - Неверный формат):**
```json
{
  "detail": "Неверный формат дескрипторов. Ожидается 128 чисел, получено 64"
}
```

#### POST /biometric/login

**Request:**
```json
{
  "descriptor": [0.123, -0.456, 0.789, ...],  // 128 чисел
  "timestamp": "2025-10-29T12:34:56.789Z",
  "version": "1.0"
}
```

**Headers:**
```
Content-Type: application/json
(БЕЗ Authorization!)
```

**Response (200 - Распознано):**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { /* userData */ }
}
```

**Response (401 - Не распознано):**
```json
{
  "detail": "Лицо не распознано. Попробуйте еще раз или войдите с паролем."
}
```

**Response (404 - Нет биометрии):**
```json
{
  "detail": "Лицо не распознано. Зарегистрируйте биометрию."
}
```

### 7.3 Обработка ошибок

**Универсальный паттерн:**

```javascript
try {
  const response = await fetch(url, options);
  const data = await response.json();

  // Проверка HTTP статуса
  if (!response.ok) {
    throw new Error(data.detail || 'Неизвестная ошибка');
  }

  // Проверка обязательных полей
  if (!data.access_token) {
    throw new Error('Не получены токены');
  }

  // Успех
  handleSuccess(data);

} catch (err) {
  // Обработка ошибок
  setStatus({ 
    type: "error", 
    message: err.message || "Произошла ошибка" 
  });
} finally {
  // Всегда выполняется
  setLoading(false);
}
```

**Типы ошибок:**

1. **Сетевые ошибки** (нет интернета, сервер недоступен)
   ```javascript
   // err.message = "Failed to fetch"
   ```

2. **HTTP ошибки** (400, 401, 500)
   ```javascript
   // response.ok = false
   // data.detail = "Email уже зарегистрирован"
   ```

3. **Ошибки валидации** (неверный формат данных)
   ```javascript
   // data.detail = "Неверный формат дескрипторов"
   ```

4. **Ошибки JS** (отсутствие обязательных полей)
   ```javascript
   // throw new Error('Не получены токены')
   ```

### 7.4 Токены (Access + Refresh)

**Access Token:**
- Время жизни: **30 минут** (1800 сек)
- Формат: JWT
- Содержит: `{user_id, email, full_name, exp, iat, type: "access"}`
- Используется: В `Authorization: Bearer <token>` для защищённых эндпоинтов

**Refresh Token:**
- Время жизни: **30 дней**
- Формат: Случайная строка (64 символа)
- Хранится: В БД (хешированный bcrypt)
- Используется: Для обновления access токена через `/refresh`

**Почему 2 токена?**
1. **Безопасность:**
   - Access токен короткий → меньше риск при утечке
   - Refresh токен длинный → не нужно часто логиниться

2. **Отзыв:**
   - Access токен нельзя отозвать (stateless JWT)
   - Refresh токен можно отозвать (хранится в БД)

**Поток обновления (будущее):**
```
1. Access токен истёк (30 минут прошло)
2. Фронт: POST /refresh {refresh_token}
3. Бэк: Проверяет refresh токен в БД → выдаёт новый access токен
4. Фронт: Обновляет localStorage
```

**Сейчас НЕ реализовано:**
- Автоматическое обновление access токена
- Перехват 401 ошибок
- Retry запросов после обновления токена

---

## 8. localStorage

### 8.1 Что хранится

```javascript
localStorage.setItem('accessToken', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...');
localStorage.setItem('refreshToken', 'a1b2c3d4e5f6...');
localStorage.setItem('userData', JSON.stringify({
  id: 1,
  email: "ivan@example.com",
  full_name: "Иван Иванов",
  phone: "+79991234567",
  birth_date: "1990-01-01",
  is_active: true,
  is_biometric_verified: true,
  created_at: "2025-10-29T12:34:56.789Z"
}));
```

### 8.2 Когда обновляется

| Событие | Действие |
|---------|----------|
| Регистрация | `setItem` (3 ключа) |
| Вход (пароль) | `setItem` (3 ключа) |
| Вход (биометрия) | `setItem` (3 ключа) |
| Обновление userData | `setItem('userData', ...)` |
| Выход | `removeItem` (3 ключа) |

### 8.3 Синхронизация с state

**При монтировании app (page.js):**

```javascript
useEffect(() => {
  if (typeof window !== 'undefined') {
    const savedAccessToken = localStorage.getItem('accessToken');
    const savedRefreshToken = localStorage.getItem('refreshToken');
    const savedUserData = localStorage.getItem('userData');
    
    // Если ВСЕ 3 ключа есть → восстанавливаем сессию
    if (savedAccessToken && savedRefreshToken && savedUserData) {
      setAccessToken(savedAccessToken);
      setRefreshToken(savedRefreshToken);
      setUserData(JSON.parse(savedUserData));
      setIsAuthenticated(true);
    }
  }
}, []);
```

**Логика:**
- localStorage → state (при загрузке страницы)
- state → localStorage (при изменении)
- Двусторонняя синхронизация

**Зачем проверка всех 3 ключей?**
- Если хотя бы 1 отсутствует → сессия невалидна
- Например, пользователь вручную удалил accessToken
- Без проверки → приложение сломается

### 8.4 Безопасность localStorage

**Уязвимости:**

1. **XSS (Cross-Site Scripting):**
   - Злоумышленник внедряет JS код
   - Код читает `localStorage.getItem('accessToken')`
   - Токен украден!

2. **Доступ из DevTools:**
   - Любой может открыть F12 → Application → Local Storage
   - Скопировать токен

**Защита:**

1. **HTTPS обязателен** - предотвращает перехват токенов
2. **Content Security Policy (CSP)** - блокирует XSS
3. **Short-lived access tokens** - 30 минут (минимальный урон при утечке)
4. **HttpOnly cookies альтернатива** - но сложнее для SPA

**Почему всё равно используем localStorage?**
- Простота для SPA (Single Page Application)
- Нет CORS проблем с cookies
- Refresh токен можно отозвать в БД

---

## 9. Безопасность

### 9.1 Хранение токенов

**Текущая реализация:**
- Access token: `localStorage`
- Refresh token: `localStorage`

**Риски:**
- XSS атака может украсть токены
- Любой JS код на странице имеет доступ

**Альтернативы (будущее):**
1. **HttpOnly cookies** - JS не имеет доступа
2. **Memory only** - токены только в RAM (теряются при перезагрузке)
3. **Encrypted localStorage** - шифрование перед сохранением

### 9.2 Защита роутов

**Текущая реализация:**

```javascript
// page.js
{isAuthenticated ? (
  <MainPage {...props} />
) : (
  <LoginPage {...props} />
)}
```

**Проблема:**
- Только клиентская проверка
- Не защищает API (бэкенд проверяет токен)

**Что защищено:**
- UI роутинг (не видишь MainPage без токена)
- API эндпоинты (бэкенд проверяет JWT)

**Что НЕ защищено:**
- Прямой доступ к компонентам (но бесполезно без токена)
- Манипуляция с `isAuthenticated` в DevTools (но API всё равно проверит)

### 9.3 Валидация на клиенте

**HTML5 валидация:**
```jsx
<input type="email" required />          // Email формат
<input type="password" minLength={8} />  // Минимум 8 символов
<input pattern="^\+7\d{10}$" />         // Телефон +7XXXXXXXXXX
```

**JS валидация:**
```javascript
// Проверка паролей
if (formData.password !== formData.confirmPassword) {
  setStatus({ type: "error", message: "Пароли не совпадают" });
  return;
}
```

**Важно:**
- Клиентская валидация = **UX** (удобство пользователя)
- Серверная валидация = **Безопасность** (защита от обхода)
- Обе нужны!

### 9.4 CORS (Cross-Origin Resource Sharing)

**Бэкенд (main.py):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Только фронтенд
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Что это даёт:**
- Браузер разрешает запросы с `localhost:3000` на `localhost:8000`
- Без CORS → браузер блокирует (Same-Origin Policy)

**В продакшене:**
```python
allow_origins=["https://life-sso.com"]  # Ваш домен
```

---

## 10. UI/UX особенности

### 10.1 Динамические импорты

**Зачем:**
- Face-API.js = **~6 MB** (тяжёлая библиотека)
- Не нужна на странице регистрации
- Загружается только когда нужна (ленивая загрузка)

**Реализация:**

```javascript
// main.js
const BiometricVerification = dynamic(() => import("./BiometricVerification"), { 
  ssr: false,  // Отключаем SSR (face-api.js работает только в браузере)
  loading: () => <div>Загрузка...</div>  // Fallback компонент
});
```

**Как работает:**
1. MainPage загружается БЕЗ face-api.js (быстро)
2. Пользователь нажимает "Верификация биометрией"
3. Next.js загружает chunk с BiometricVerification
4. Показывает "Загрузка..." пока грузится
5. Рендерит BiometricVerification

**Выигрыш:**
- Начальная загрузка: **-6 MB**
- Time to Interactive: **быстрее на 2-3 сек**

### 10.2 Обратный отсчёт (3-2-1)

**Визуальный feedback:**

```jsx
{countdown !== null && countdown > 0 && (
  <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
    <div className="text-white text-8xl font-bold animate-pulse">
      {countdown}
    </div>
  </div>
)}
```

**CSS (Tailwind):**
- `absolute inset-0` - поверх всего контейнера
- `text-8xl` - огромный размер (96px)
- `animate-pulse` - пульсация (opacity 0% → 100% → 0%)
- `bg-black bg-opacity-30` - полупрозрачный фон

**Зачем:**
- Пользователь видит что происходит
- Может подготовиться (3 секунды на правильную позу)
- Избегает внезапной отправки

### 10.3 Статусы загрузки

**Паттерн:**

```javascript
const [loading, setLoading] = useState(false);
const [status, setStatus] = useState(null);

// Перед запросом
setLoading(true);
setStatus(null);

try {
  // ... запрос ...
  setStatus({ type: "success", message: "Успех!" });
} catch (err) {
  setStatus({ type: "error", message: err.message });
} finally {
  setLoading(false);
}
```

**UI:**

```jsx
{loading && <Spinner />}

{status && (
  <div className={status.type === "success" ? "bg-green-100" : "bg-red-100"}>
    {status.message}
  </div>
)}
```

**Состояния:**
1. **Idle** - `loading = false`, `status = null` (форма видна)
2. **Loading** - `loading = true`, `status = null` (спиннер)
3. **Success** - `loading = false`, `status = {type: "success", ...}` (зелёный)
4. **Error** - `loading = false`, `status = {type: "error", ...}` (красный)

### 10.4 Визуальный feedback (Ориентация лица)

**Реал-тайм подсказки:**

```jsx
{faceDetected ? (
  <div className={orientationStatus.isLookingStraight ? 'text-green-600' : 'text-orange-600'}>
    <svg>...</svg>
    {orientationStatus.message}
  </div>
) : (
  <div className="text-red-600">
    Лицо не обнаружено
  </div>
)}
```

**Цвета:**
- 🟢 Зелёный - лицо прямо ("Отлично! Держите так")
- 🟠 Оранжевый - лицо не прямо ("Поверните голову влево")
- 🔴 Красный - лицо не найдено

**Иконки:**
- ✓ (галочка) - успех
- ⚠ (треугольник) - предупреждение
- ✗ (крестик) - ошибка

### 10.5 Canvas overlay

**Зелёные точки и рамка:**

```jsx
<div className="relative">
  <Webcam ref={webcamRef} />
  <canvas ref={canvasRef} className="absolute top-0 left-0" />
</div>
```

**Рендеринг каждые 300мс:**
```javascript
drawFaceBox(canvasRef.current, video, detection);
// Рисует:
// - Зелёную рамку вокруг лица
// - 68 зелёных точек (landmarks)
// - Процент уверенности (95%)
```

**CSS tricks:**
- `position: relative` на родителе
- `position: absolute` на canvas
- Canvas накладывается поверх видео
- `pointer-events: none` - клики проходят сквозь canvas

---

## Заключение

### Основные концепции

1. **Централизованный state** - `page.js` управляет всем
2. **Props drilling** - данные передаются вниз, callbacks вверх
3. **localStorage синхронизация** - персистентность сессии
4. **Dynamic imports** - оптимизация загрузки
5. **Face-API.js** - распознавание лиц на клиенте
6. **JWT токены** - безопасная аутентификация
7. **Автоматическая отправка** - UX без лишних кликов

### Архитектурные решения

✅ **Что сделано хорошо:**
- Чистое разделение компонентов
- Единый источник правды (single source of truth)
- Обработка ошибок
- Визуальный feedback
- Реал-тайм детекция

⚠️ **Что можно улучшить:**
- Context API вместо props drilling
- Автоматическое обновление access токена
- Encrypted localStorage
- Service Worker для офлайн режима
- Тесты (unit + integration)

### Следующие шаги

1. **Обновление токенов** - перехват 401, автообновление
2. **Context API** - избавиться от props drilling
3. **Error boundaries** - обработка критических ошибок
4. **Performance** - мемоизация (useMemo, useCallback)
5. **Accessibility** - ARIA атрибуты, keyboard navigation
6. **i18n** - мультиязычность (RU/EN/KZ)

---

**Документация создана: 29.10.2025**
**Версия: 1.0.0**
**Автор: Life SSO Team**




