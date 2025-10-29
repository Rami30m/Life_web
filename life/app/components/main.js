"use client";

import { useState } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";

// Динамический импорт BiometricVerification (загрузка только при необходимости)
const BiometricVerification = dynamic(() => import("./BiometricVerification"), { 
  ssr: false,
  loading: () => <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-300">
    <div className="text-blue-700 font-medium">Загрузка...</div>
  </div>
});

export default function MainPage({ userData, accessToken, onLogout, onUserUpdate }) {
  const [showCard, setShowCard] = useState(false);
  const [showBiometric, setShowBiometric] = useState(false);
  const [biometricVerified, setBiometricVerified] = useState(false);

  const handleBiometricSuccess = (updatedUser) => {
    setBiometricVerified(true);
    setShowBiometric(false);
    
    // Обновляем данные пользователя
    if (updatedUser && onUserUpdate) {
      onUserUpdate(updatedUser);
    }
  };

  // Если открыт компонент биометрии, показываем его
  if (showBiometric) {
    return (
      <BiometricVerification 
        accessToken={accessToken}
        onSuccess={handleBiometricSuccess}
        onCancel={() => setShowBiometric(false)}
      />
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-100 to-green-300 p-4">
      <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-lg text-center">
        {/* Приветствие пользователя */}
          <div className="mb-6 pb-6 border-b border-green-200">
            <h2 className="text-2xl font-bold text-green-700">
              Добро пожаловать, {userData?.full_name?.split(' ')[0] || 'Пользователь'}! 👋
            </h2>
            <p className="text-sm text-gray-600 mt-2">{userData?.email}</p>
            
            {/* Статус верификации */}
            <div className="mt-3 flex items-center justify-center gap-2">
              {userData?.is_biometric_verified ? (
                <div className="inline-flex items-center gap-2 bg-green-100 text-green-700 px-4 py-2 rounded-full border border-green-300">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="font-semibold text-sm">Аккаунт верифицирован</span>
                </div>
              ) : (
                <div className="inline-flex items-center gap-2 bg-orange-100 text-orange-700 px-4 py-2 rounded-full border border-orange-300">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <span className="font-semibold text-sm">Требуется верификация</span>
                </div>
              )}
            </div>
          </div>

        <h2 className="text-2xl font-bold text-green-700 mb-6">
          Цифровое удостоверение
        </h2>

        <div className="space-y-4">
          <button
            onClick={() => alert("Создание цифрового удостоверения...")}
            className="w-full bg-green-600 text-white py-3 rounded-lg font-medium hover:bg-green-700 transition-colors"
          >
            Создать цифровое удостоверение
          </button>

          <button
            onClick={() => setShowCard(!showCard)}
            className="w-full bg-green-100 text-green-700 py-3 rounded-lg font-medium hover:bg-green-200 border border-green-300 transition-colors"
          >
            {showCard ? "Скрыть удостоверение" : "Показать цифровое удостоверение"}
          </button>
        </div>

        {/* Поле для отображения удостоверения */}
        {showCard && (
          <div className="mt-6 flex justify-center">
            <div className="w-80 h-48 bg-white border border-green-300 rounded-xl shadow-md flex items-center justify-between px-5 py-4">
              <div className="text-left">
                <h3 className="text-lg font-semibold text-green-800">{userData?.full_name || 'Иван Иванов'}</h3>
                <p className="text-sm text-green-700 mt-1">Телефон: {userData?.phone || '+7 777 123 4567'}</p>
                <p className="text-sm text-green-700">Email: {userData?.email || 'user@example.com'}</p>
                <p className="text-xs text-gray-600 mt-1">Дата рождения: {userData?.birth_date || '01.01.1990'}</p>
              </div>
              <div className="flex-shrink-0">
                <div className="w-16 h-16 bg-green-100 rounded-md border border-green-300 flex items-center justify-center">
                  <svg className="w-12 h-12 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Биометрическая верификация */}
        <div className="mt-10 space-y-3">
          <button 
            onClick={() => setShowBiometric(true)}
            className={`w-full py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
              biometricVerified 
                ? "bg-green-100 text-green-700 border-2 border-green-400"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {biometricVerified ? (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Биометрия верифицирована ✓
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Верификация биометрией
              </>
            )}
          </button>
          
          <button className="w-full bg-gray-100 text-gray-500 py-3 rounded-lg cursor-not-allowed">
            (новая функция)
          </button>
        </div>

        {/* Кнопка выхода */}
        <div className="mt-8 pt-6 border-t border-green-200">
          <button 
            onClick={onLogout}
            className="w-full bg-red-500 text-white py-3 rounded-lg font-medium hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Выйти из аккаунта
          </button>
        </div>
      </div>
    </div>
  );
}
