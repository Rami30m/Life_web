"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

// Динамический импорт BiometricLogin
const BiometricLogin = dynamic(() => import("./BiometricLogin"), { ssr: false });

export default function LoginPage({ onSwitch, onSuccess }) {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBiometricLogin, setShowBiometricLogin] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    try {
      // Отправка данных на backend
      const { API_BASE } = await import('../utils/apiBase');
      const response = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Неверный email или пароль');
      }

      // Проверяем что получили токены
      if (!data.access_token || !data.refresh_token) {
        throw new Error('Не получены токены авторизации');
      }

      // Сразу переходим на главную страницу (без задержки)
      onSuccess(
        data.user, // Данные пользователя из бэкенда
        {
          access_token: data.access_token,
          refresh_token: data.refresh_token
        }
      );
    } catch (err) {
      // Обработка ошибки
      setStatus({ type: "error", message: err.message || "Ошибка при входе. Попробуйте снова." });
    } finally {
      setLoading(false);
    }
  };

  // Если открыт компонент биометрического входа
  if (showBiometricLogin) {
    return (
      <BiometricLogin
        onSuccess={onSuccess}
        onCancel={() => setShowBiometricLogin(false)}
      />
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 transition-all duration-300 ">
        <h1 className="text-3xl font-bold text-center text-green-700 mb-6">
          Вход в Life 🌱
        </h1>

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

          <p className="text-center text-sm text-gray-600 mt-3">
            Нет аккаунта?{" "}
            <button
    type="button"
    onClick={onSwitch}
    className="text-green-600 hover:underline font-medium"
  >
    Зарегистрироваться
  </button>
          </p>

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
