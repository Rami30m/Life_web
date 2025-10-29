"use client";

import { useState } from "react";

export default function LoginECPPage({ onSwitch }) {
  const [formData, setFormData] = useState({
    certificateFile: null,
    pin: "",
  });

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    if (e.target.name === "certificateFile") {
      setFormData({ ...formData, certificateFile: e.target.files[0] });
    } else {
      setFormData({ ...formData, [e.target.name]: e.target.value });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    try {
      // 🔹 Здесь позже будет запрос к backend для проверки ЭЦП
      await new Promise((res) => setTimeout(res, 1500)); // имитация запроса

      // Пример успешной аутентификации через ЭЦП:
      setStatus({ type: "success", message: "Вход через ЭЦП прошел успешно!" });
    } catch (err) {
      // Пример ошибки:
      setStatus({ type: "error", message: "Ошибка при проверке ЭЦП. Проверьте сертификат и PIN-код." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 transition-all duration-300">
        <h1 className="text-3xl font-bold text-center text-green-700 mb-6">
          Вход через ЭЦП 🔐
        </h1>

        {!status && !loading && (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Сертификат ЭЦП
              </label>
              <div className="relative">
                <input
                  type="file"
                  name="certificateFile"
                  onChange={handleChange}
                  accept=".p12,.pfx,.crt,.cer"
                  required
                  className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400 file:mr-4 file:py-1 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Поддерживаемые форматы: .p12, .pfx, .crt, .cer
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PIN-код сертификата
              </label>
              <input
                type="password"
                name="pin"
                value={formData.pin}
                onChange={handleChange}
                required
                className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-400"
                placeholder="Введите PIN-код"
              />
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">
                    Информация о безопасности
                  </h3>
                  <div className="mt-1 text-sm text-blue-700">
                    <p>• Ваш сертификат обрабатывается локально</p>
                    <p>• PIN-код не передается на сервер</p>
                    <p>• Используется криптографическая защита</p>
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="w-full bg-green-600 text-white font-semibold py-2 rounded-lg hover:bg-green-700 transition-all duration-200"
            >
              Войти через ЭЦП
            </button>

            <p className="text-center text-sm text-gray-600 mt-3">
              Нет сертификата?{" "}
              <button
                type="button"
                onClick={onSwitch}
                className="text-green-600 hover:underline font-medium"
              >
                Обычный вход
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
              <span className="ml-3 text-green-700 font-medium">Проверка сертификата...</span>
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



