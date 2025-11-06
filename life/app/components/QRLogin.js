"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";

const BiometricLogin = dynamic(() => import("./BiometricLogin"), { ssr: false });

import { API_BASE } from "../utils/apiBase";

export default function QRLogin({ onSuccess, onCancel, clientId, redirectUri, state, scope }) {
  const [step, setStep] = useState("initiate"); // initiate, scanning, authorized
  const [qrData, setQrData] = useState(null);
  const [userCode, setUserCode] = useState("");
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBiometricLogin, setShowBiometricLogin] = useState(false);
  const [deviceCode, setDeviceCode] = useState("");
  const pollingIntervalRef = useRef(null);

  // Инициализация QR сессии
  useEffect(() => {
    if (step === "initiate" && clientId) {
      initiateQR();
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [step, clientId]);

  const initiateQR = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/sso/qr/initiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          scope: scope || "openid profile email",
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Ошибка инициации QR");
      }

      const data = await response.json();
      setQrData(data);
      setDeviceCode(data.device_code);
      setUserCode(data.user_code);
      setStep("scanning");

      // Начинаем polling
      startPolling(data.device_code, clientId);
    } catch (err) {
      setStatus({ type: "error", message: err.message });
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (deviceCode, clientId) => {
    // Получаем client_secret из localStorage (если есть) или запрашиваем у пользователя
    // В реальном приложении это должно быть защищено
    const clientSecret = prompt("Введите client_secret для polling (для теста):");
    if (!clientSecret) {
      setStatus({ type: "error", message: "Необходим client_secret для проверки статуса" });
      return;
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/sso/qr/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            device_code: deviceCode,
            client_id: clientId,
            client_secret: clientSecret,
          }),
        });

        if (!response.ok) {
          const error = await response.json();
          if (error.detail?.includes("истек")) {
            clearInterval(pollingIntervalRef.current);
            setStatus({ type: "error", message: "QR-код истек. Запросите новый." });
            setStep("initiate");
          }
          return;
        }

        const data = await response.json();

        if (data.status === "authorized") {
          clearInterval(pollingIntervalRef.current);
          setStep("authorized");

          // Если есть onSuccess, вызываем его
          if (onSuccess) {
            onSuccess(data.user, {
              access_token: data.access_token,
              refresh_token: data.refresh_token,
            });
          }
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 5000); // Каждые 5 секунд
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(`${API_BASE}/sso/qr/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          user_code: userCode,
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Ошибка входа");
      }

      // Вход успешен - polling получит токены
      setStatus({ type: "success", message: "Вход выполнен! Ожидание токенов..." });
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleBiometricSuccess = (user, tokens) => {
    // После биометрического входа нужно тоже выполнить вход по QR
    // Это можно сделать через тот же endpoint /sso/qr/verify
    // Но для биометрии нужно получить email пользователя
    if (user && user.email && userCode) {
      // Автоматически отправляем запрос на вход
      fetch(`${API_BASE}/sso/qr/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          user_code: userCode,
          email: user.email,
          password: "", // Для биометрии пароль не нужен, но endpoint может требовать
        }),
      });
    }
  };

  if (showBiometricLogin) {
    return (
      <BiometricLogin onSuccess={handleBiometricSuccess} onCancel={() => setShowBiometricLogin(false)} />
    );
  }

  if (step === "initiate" || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-300 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md text-center">
          <h1 className="text-2xl font-bold text-blue-700 mb-4">📱 QR Code Вход</h1>
          {loading && <p className="text-gray-600">Инициализация QR-кода...</p>}
        </div>
      </div>
    );
  }

  if (step === "scanning" && qrData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-300 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md">
          <h1 className="text-2xl font-bold text-blue-700 mb-4 text-center">📱 QR Code Вход</h1>

          {/* Отображение QR кода или ссылки */}
          <div className="mb-6 text-center">
            <div className="bg-gray-100 p-4 rounded-lg mb-4">
              <p className="text-sm text-gray-600 mb-2">User Code:</p>
              <p className="text-2xl font-bold text-blue-700 tracking-wider">{userCode}</p>
            </div>
            <p className="text-sm text-gray-600">
              Откройте эту ссылку на другом устройстве или отсканируйте QR:
            </p>
            <a
              href={qrData.verification_uri_complete}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline break-all text-xs mt-2 inline-block"
            >
              {qrData.verification_uri_complete}
            </a>
          </div>

          {/* Форма входа для текущего устройства */}
          <div className="border-t pt-4">
            <p className="text-sm text-gray-600 mb-4 text-center">Или войдите здесь:</p>

            {status && (
              <div
                className={`mb-4 p-3 rounded ${
                  status.type === "error" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                }`}
              >
                {status.message}
              </div>
            )}

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <input
                type="email"
                name="email"
                placeholder="Email"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="password"
                name="password"
                placeholder="Пароль"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
              >
                {loading ? "Вход..." : "Войти"}
              </button>
            </form>

            <div className="mt-4 text-center">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">или</span>
                </div>
              </div>
              <button
                onClick={() => setShowBiometricLogin(true)}
                className="mt-4 w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600"
              >
                Войти по лицу
              </button>
            </div>
          </div>

          {onCancel && (
            <button
              onClick={onCancel}
              className="mt-4 w-full text-gray-600 hover:text-gray-800"
            >
              Отмена
            </button>
          )}
        </div>
      </div>
    );
  }

  if (step === "authorized") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md text-center">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-green-700 mb-4">Авторизация успешна!</h1>
          <p className="text-gray-600">Вы можете закрыть эту страницу.</p>
        </div>
      </div>
    );
  }

  return null;
}

