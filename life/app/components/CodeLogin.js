"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const BiometricLogin = dynamic(() => import("./BiometricLogin"), { ssr: false });

const API_BASE = "http://localhost:8000";

export default function CodeLogin({ onSuccess, onCancel, clientId, redirectUri }) {
  const [step, setStep] = useState("request"); // request, verify
  const [identifier, setIdentifier] = useState("");
  const [codeData, setCodeData] = useState(null);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBiometricLogin, setShowBiometricLogin] = useState(false);

  const handleRequestCode = async (e) => {
    e.preventDefault();
    if (!identifier.trim()) {
      setStatus({ type: "error", message: "Введите email или имя" });
      return;
    }

    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(`${API_BASE}/sso/code/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          identifier: identifier,
          redirect_uri: redirectUri,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Ошибка запроса кода");
      }

      const data = await response.json();
      setCodeData(data);
      setCode(data.code); // Показываем код пользователю
      setStep("verify");
      setStatus({
        type: "success",
        message: `Код получен: ${data.code}`,
      });
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    if (!code.trim() || code.length !== 6) {
      setStatus({ type: "error", message: "Введите 6-цифровой код" });
      return;
    }

    setLoading(true);
    setStatus(null);

    // Для проверки кода нужен client_secret
    // В реальном приложении это должно быть на бэкенде платформы
    const clientSecret = prompt("Введите client_secret (для теста):");
    if (!clientSecret) {
      setStatus({ type: "error", message: "Необходим client_secret" });
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/sso/code/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          client_secret: clientSecret,
          code_id: codeData.code_id,
          code: code,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Неверный код");
      }

      const data = await response.json();

      // Если есть redirect_uri, редиректим на платформу с токенами
      if (redirectUri && codeData.redirect_uri) {
        const redirectUrl = new URL(codeData.redirect_uri);
        redirectUrl.searchParams.set("access_token", data.access_token);
        redirectUrl.searchParams.set("refresh_token", data.refresh_token);
        redirectUrl.searchParams.set("token_type", data.token_type);
        redirectUrl.searchParams.set("expires_in", data.expires_in.toString());
        window.location.href = redirectUrl.toString();
        return;
      }

      // Если есть onSuccess, вызываем его
      if (onSuccess) {
        onSuccess(data.user, {
          access_token: data.access_token,
          refresh_token: data.refresh_token,
        });
      }
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  };

  if (showBiometricLogin) {
    return (
      <BiometricLogin
        onSuccess={(user, tokens) => {
          // После биометрического входа можно запросить код для входа на платформу
          // Но это не стандартный flow, поэтому просто закрываем
          setShowBiometricLogin(false);
        }}
        onCancel={() => setShowBiometricLogin(false)}
      />
    );
  }

  if (step === "request") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 to-purple-300 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md">
          <h1 className="text-2xl font-bold text-purple-700 mb-4 text-center">🔢 Вход по коду</h1>

          {status && (
            <div
              className={`mb-4 p-3 rounded ${
                status.type === "error" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
              }`}
            >
              {status.message}
            </div>
          )}

          <form onSubmit={handleRequestCode} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email или имя пользователя
              </label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="user@example.com или Имя Фамилия"
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
            >
              {loading ? "Запрос кода..." : "Получить код"}
            </button>
          </form>

          {onCancel && (
            <button onClick={onCancel} className="mt-4 w-full text-gray-600 hover:text-gray-800">
              Отмена
            </button>
          )}
        </div>
      </div>
    );
  }

  if (step === "verify") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 to-purple-300 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md">
          <h1 className="text-2xl font-bold text-purple-700 mb-4 text-center">🔢 Введите код</h1>

          {codeData && (
            <div className="mb-6 text-center">
              <p className="text-sm text-gray-600 mb-2">Код отправлен:</p>
              <div className="bg-purple-100 p-4 rounded-lg">
                <p className="text-3xl font-bold text-purple-700 tracking-wider">{code}</p>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Введите этот код ниже или скопируйте его
              </p>
            </div>
          )}

          {status && (
            <div
              className={`mb-4 p-3 rounded ${
                status.type === "error" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
              }`}
            >
              {status.message}
            </div>
          )}

          <form onSubmit={handleVerifyCode} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">6-цифровой код</label>
              <input
                type="text"
                value={code}
                onChange={(e) => {
                  // Ограничиваем только цифрами и максимум 6 символов
                  const value = e.target.value.replace(/\D/g, "").slice(0, 6);
                  setCode(value);
                }}
                placeholder="123456"
                maxLength={6}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-center text-2xl tracking-widest"
              />
            </div>

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
            >
              {loading ? "Проверка..." : "Войти"}
            </button>
          </form>

          <button
            onClick={() => {
              setStep("request");
              setCode("");
              setCodeData(null);
              setStatus(null);
            }}
            className="mt-4 w-full text-gray-600 hover:text-gray-800"
          >
            Запросить новый код
          </button>

          {onCancel && (
            <button onClick={onCancel} className="mt-2 w-full text-gray-600 hover:text-gray-800">
              Отмена
            </button>
          )}
        </div>
      </div>
    );
  }

  return null;
}

