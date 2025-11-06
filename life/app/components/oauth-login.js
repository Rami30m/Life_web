"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";

// Динамический импорт BiometricLogin
const BiometricLogin = dynamic(() => import("./BiometricLogin"), { ssr: false });

export default function OAuthLoginPage() {
  const searchParams = useSearchParams();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBiometricLogin, setShowBiometricLogin] = useState(false);
  const [isBiometricProcessing, setIsBiometricProcessing] = useState(false); // Защита от повторных вызовов
  
  // Получаем параметры из URL
  const clientId = searchParams.get('client_id');
  const redirectUri = searchParams.get('redirect_uri');
  const state = searchParams.get('state');
  const scope = searchParams.get('scope');
  const platformName = searchParams.get('platform_name') || 'платформу';

  useEffect(() => {
    // Проверяем что все необходимые параметры есть
    if (!clientId || !redirectUri) {
      setStatus({
        type: "error",
        message: "Отсутствуют обязательные параметры (client_id, redirect_uri)"
      });
    }
  }, [clientId, redirectUri]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!clientId || !redirectUri) return;

    setLoading(true);
    setStatus(null);

    try {
      // Отправка данных на backend
      const { API_BASE } = await import('../utils/apiBase');
      const response = await fetch(`${API_BASE}/sso/authorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          client_id: clientId,
          redirect_uri: redirectUri,
          state: state || '',
          scope: scope || 'openid profile email',
          email: formData.email,
          password: formData.password
        })
      });

      // Бэкенд возвращает RedirectResponse (302) с Location header
      // Проверяем заголовок Location (редирект)
      if (response.status === 302 || response.status === 200) {
        const location = response.headers.get('Location');
        if (location) {
          window.location.href = location;
          return;
        }
      }

      // Если fetch автоматически следует редиректу (response.redirected)
      if (response.redirected && response.url) {
        window.location.href = response.url;
        return;
      }

      // Если сервер вернул HTML (статус 200, но с редиректом внутри)
      const contentType = response.headers.get('Content-Type') || '';
      if (contentType.includes('text/html')) {
        const text = await response.text();
        
        // Ищем редирект в HTML (meta refresh или JavaScript)
        const metaMatch = text.match(/<meta[^>]*http-equiv=["']refresh["'][^>]*url=["']([^"']+)["']/i);
        if (metaMatch) {
          window.location.href = metaMatch[1];
          return;
        }
        
        const jsMatch = text.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
        if (jsMatch) {
          window.location.href = jsMatch[1];
          return;
        }
      }

      // Если получили JSON с ошибкой
      if (contentType.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Неверный email или пароль');
        }
      } else if (!response.ok) {
        // Если не JSON и не успешный ответ
        throw new Error('Ошибка сервера при обработке входа');
      }

    } catch (err) {
      setStatus({
        type: "error",
        message: err.message || "Ошибка при входе"
      });
      setLoading(false);
    }
  };

  const handleBiometricSuccess = (user, tokens, descriptor) => {
    // Защита от повторных вызовов
    if (isBiometricProcessing) {
      console.log('⚠️ Биометрический вход уже обрабатывается, пропускаем повторный вызов');
      return;
    }

    // После успешного биометрического входа тоже нужно создать authorization code
    // Используем тот же дескриптор, что был использован для входа
    if (clientId && redirectUri && descriptor) {
      setIsBiometricProcessing(true); // Устанавливаем флаг обработки
      // Импортируем функцию для форматирования дескриптора
      import('../utils/faceApi').then(({ formatDescriptorForServer }) => {
        // Используем тот же подход, что и при обычном входе через email/password
        const { API_BASE } = await import('../utils/apiBase');
        fetch(`${API_BASE}/sso/authorize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          // БЕЗ redirect: 'manual' - пусть fetch автоматически следует редиректу
          body: new URLSearchParams({
            client_id: clientId,
            redirect_uri: redirectUri,
            state: state || '',
            scope: scope || 'openid profile email',
            biometric_descriptor: formatDescriptorForServer(descriptor) // Отправляем дескриптор
          })
        }).then(async response => {
          // Бэкенд возвращает RedirectResponse (302) с Location header
          // Проверяем заголовок Location (редирект)
          if (response.status === 302 || response.status === 200) {
            const location = response.headers.get('Location');
            if (location) {
              window.location.href = location;
              return;
            }
          }

          // Если fetch автоматически следует редиректу (response.redirected)
          if (response.redirected && response.url) {
            window.location.href = response.url;
            return; // Редирект выполнен, функция завершается
          }

          // Если получили 429 - rate limit
          if (response.status === 429) {
            const errorData = await response.json().catch(() => ({ detail: 'Превышен лимит запросов' }));
            throw new Error(errorData.detail || 'Слишком много запросов. Попробуйте через минуту.');
          }

          // Если сервер вернул HTML (статус 200, но с редиректом внутри)
          const contentType = response.headers.get('Content-Type') || '';
          if (contentType.includes('text/html')) {
            const text = await response.text();
            
            // Ищем редирект в HTML (meta refresh или JavaScript)
            const metaMatch = text.match(/<meta[^>]*http-equiv=["']refresh["'][^>]*url=["']([^"']+)["']/i);
            if (metaMatch) {
              window.location.href = metaMatch[1];
              return;
            }
            
            const jsMatch = text.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
            if (jsMatch) {
              window.location.href = jsMatch[1];
              return;
            }
          }

          // Если получили JSON с ошибкой
          if (contentType.includes('application/json')) {
            const data = await response.json();
            if (!response.ok) {
              throw new Error(data.detail || 'Ошибка при создании authorization code');
            }
          } else if (!response.ok) {
            // Если не JSON и не успешный ответ
            throw new Error('Ошибка сервера при обработке входа');
          }
        }).catch(err => {
          setIsBiometricProcessing(false); // Сбрасываем флаг при ошибке
          setStatus({
            type: "error",
            message: err.message || "Ошибка при входе"
          });
        });
      }).catch(err => {
        console.error('❌ Ошибка импорта faceApi:', err);
        setStatus({
          type: "error",
          message: 'Ошибка загрузки модуля для обработки биометрии'
        });
      });
    } else {
      setStatus({
        type: "error",
        message: "Отсутствуют необходимые данные для OAuth авторизации"
      });
    }
  };

  // Если открыт биометрический вход
  if (showBiometricLogin) {
    return (
      <BiometricLogin 
        onSuccess={handleBiometricSuccess}
        onCancel={() => setShowBiometricLogin(false)}
      />
    );
  }

  // Если нет обязательных параметров
  if (!clientId || !redirectUri) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-100 to-red-300">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Ошибка авторизации</h1>
          <p className="text-gray-700">Отсутствуют обязательные параметры для OAuth авторизации.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 transition-all duration-300">
        <h1 className="text-3xl font-bold text-center text-green-700 mb-2">
          Вход в Life 🌱
        </h1>
        {platformName && (
          <p className="text-center text-gray-600 mb-6">
            Вход на платформу: <strong>{platformName}</strong>
          </p>
        )}

        {!status && !loading && (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="example@mail.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Пароль
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Введите пароль"
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="text-green-600 focus:ring-green-500 rounded"
                />
                <span className="text-gray-600">Запомнить меня</span>
              </label>
              <a
                href="#"
                className="text-green-700 font-semibold hover:underline"
              >
                Забыли пароль?
              </a>
            </div>

            <button
              type="submit"
              className="w-full bg-green-600 text-white font-semibold py-2 rounded-lg hover:bg-green-700 transition-all duration-200"
            >
              Войти
            </button>

            {/* Разделитель */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">или</span>
              </div>
            </div>

            {/* Кнопка входа по биометрии */}
            <button
              type="button"
              onClick={() => setShowBiometricLogin(true)}
              className="w-full bg-purple-600 text-white font-semibold py-3 rounded-lg hover:bg-purple-700 transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Войти по лицу
            </button>
          </form>
        )}

        {loading && (
          <div className="flex justify-center mt-4">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-3 h-3 bg-green-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-3 h-3 bg-green-500 rounded-full animate-bounce"></div>
              <span className="ml-3 text-green-700 font-medium">Загрузка...</span>
            </div>
          </div>
        )}

        {status && !loading && (
          <div
            className={`mt-6 p-3 rounded-lg text-center font-medium transition-all duration-300 ${
              status.type === "success"
                ? "bg-green-100 text-green-700 border border-green-300"
                : "bg-red-100 text-red-700 border border-red-300"
            }`}
          >
            {status.message}
          </div>
        )}
      </div>
    </div>
  );
}

