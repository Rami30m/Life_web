"use client";

import { useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import NextDynamic from "next/dynamic";

const BiometricLogin = NextDynamic(() => import("../../../components/BiometricLogin"), { ssr: false });

import { API_BASE } from "@/app/utils/apiBase";

export const dynamic = 'force-dynamic';

function QRVerifyInner() {
  const searchParams = useSearchParams();
  const userCode = searchParams.get("user_code");
  
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBiometricLogin, setShowBiometricLogin] = useState(false);
  const [authorized, setAuthorized] = useState(false);

  // Если нет user_code, показываем ошибку
  if (!userCode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-100 to-red-300">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Ошибка</h1>
          <p className="text-gray-700">QR-код недействителен или истек</p>
        </div>
      </div>
    );
  }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    try {
      // Используем правильный эндпоинт - тот же что и на бэкенде для POST /sso/qr/verify
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

      // Вход успешен
      setAuthorized(true);
    } catch (err) {
      setStatus({ type: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleBiometricSuccess = (user, tokens) => {
    // После биометрического входа отправляем форму
    setFormData({ email: user.email, password: "" });
    // Можно автоматически отправить, но лучше показать сообщение
    setStatus({ type: "success", message: "Биометрический вход выполнен. Вход по QR обрабатывается..." });
    setShowBiometricLogin(false);
  };

  if (showBiometricLogin) {
    return (
      <BiometricLogin onSuccess={handleBiometricSuccess} onCancel={() => setShowBiometricLogin(false)} />
    );
  }

  if (authorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md text-center">
          <div className="text-6xl mb-4">✅</div>
          <h1 className="text-2xl font-bold text-green-700 mb-4">Авторизация успешна!</h1>
          <p className="text-gray-600">Вы можете закрыть эту страницу.</p>
          <p className="text-sm text-gray-500 mt-2">Платформа получит уведомление о вашем входе.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-300 p-4">
      <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md">
        <h1 className="text-2xl font-bold text-blue-700 mb-2 text-center">🔐 Life SSO</h1>
        <p className="text-center text-gray-600 mb-4">Вход по QR-коду</p>
        
        <div className="mb-6 bg-blue-50 p-4 rounded-lg text-center">
          <p className="text-sm text-gray-600 mb-2">User Code:</p>
          <p className="text-2xl font-bold text-blue-700 tracking-wider">{userCode}</p>
        </div>

        {status && (
          <div
            className={`mb-4 p-3 rounded ${
              status.type === "error" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
            }`}
          >
            {status.message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
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

        <div className="mt-6 text-center">
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
    </div>
  );
}

export default function QRVerifyPage() {
  return (
    <Suspense fallback={null}>
      <QRVerifyInner />
    </Suspense>
  );
}

