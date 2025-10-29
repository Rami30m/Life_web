"use client";

import { useState } from "react";

export default function RegisterPage({ onSwitch, onSuccess }) {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    fullName: "",
    phone: "",
    birthDate: "",
  });

  const [status, setStatus] = useState(null); // ✅ состояние для успеха или ошибки
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    // 🔹 Пример проверки на совпадение паролей
    if (formData.password !== formData.confirmPassword) {
      setStatus({ type: "error", message: "Пароли не совпадают" });
      setLoading(false);
      return;
    }

    try {
      // 🔹 Отправка данных на backend
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

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Ошибка при регистрации');
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
      // Пример ошибки:
      setStatus({ type: "error", message: err.message || "Ошибка при регистрации. Попробуйте снова." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 transition-all duration-300 ">
        <h1 className="text-3xl font-bold text-center text-green-700 mb-6">
          Регистрация в Life 🌱
        </h1>

        {!status && !loading && (
            <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ФИО
            </label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              required
              className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
              placeholder="Введите ФИО"
            />
          </div>

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
              Номер телефона
            </label>
            <input
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              required
              className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
              placeholder="+7 700 000 00 00"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата рождения
            </label>
            <input
              type="date"
              name="birthDate"
              value={formData.birthDate}
              onChange={handleChange}
              required
              className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Подтверждение пароля
              </label>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Повторите пароль"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full text-white font-semibold py-2 rounded-lg transition-all duration-200 ${
              loading
                ? "bg-green-400 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-700"
            }`}
          >
            {loading ? "Регистрация..." : "Зарегистрироваться"}
          </button>

          <p className="text-center text-sm text-gray-600 mt-3">
            Уже есть аккаунт?{" "}
            <button
    type="button"
    onClick={onSwitch}
    className="text-green-600 hover:underline font-medium"
  >
    Войти
  </button>
          </p>
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

        {/* ✅ Блок сообщения */}
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
