"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";

// Динамический импорт html5-qrcode только на клиенте
let Html5Qrcode = null;
if (typeof window !== "undefined") {
  try {
    Html5Qrcode = require("html5-qrcode").Html5Qrcode;
  } catch (e) {
    console.error("html5-qrcode не установлена:", e);
  }
}

export default function QRScanner({ onScan, onCancel }) {
  const [status, setStatus] = useState("initializing");
  const [error, setError] = useState(null);
  const scannerContainerRef = useRef(null);
  const qrCodeScannerRef = useRef(null);
  const statusRef = useRef("initializing");
  const isScanningRef = useRef(false);

  // Синхронизируем ref со state
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    let isMounted = true;
    
    const handleQRScanned = (decodedText) => {
      console.log("QR-код отсканирован:", decodedText);
      
      // Останавливаем сканер после успешного сканирования
      stopScanner();
      
      // Извлекаем user_code из URL
      try {
        const urlObj = new URL(decodedText);
        const userCode = urlObj.searchParams.get("user_code");
        if (userCode) {
          // Редиректим на страницу верификации
          window.location.href = `/sso/qr/verify?user_code=${userCode}`;
        } else {
          setError("QR-код не содержит user_code. Убедитесь, что это правильный QR-код от платформы.");
          setStatus("error");
          // Перезапускаем сканер через 2 секунды
          setTimeout(() => {
            isScanningRef.current = false;
          }, 2000);
        }
      } catch (err) {
        setError("Неверный формат QR-кода. Убедитесь, что это правильный QR-код от платформы.");
        setStatus("error");
        // Перезапускаем сканер через 2 секунды
        setTimeout(() => {
          isScanningRef.current = false;
        }, 2000);
      }
    };
    
    const initializeQRScanner = async () => {
      if (!Html5Qrcode) {
        setError("Библиотека для сканирования QR-кодов недоступна. Пожалуйста, обновите страницу.");
        setStatus("error");
        return;
      }
      
      // Даем React время отрендерить компонент
      await new Promise(resolve => setTimeout(resolve, 100));
      
      if (!isMounted || !scannerContainerRef.current) {
        return;
      }
      
      try {
        setStatus("starting");
        setError(null);
        
        const scannerId = "qr-scanner-container";
        scannerContainerRef.current.id = scannerId;
        
        // Создаем экземпляр сканера
        const qrCodeScanner = new Html5Qrcode(scannerId);
        qrCodeScannerRef.current = qrCodeScanner;
        
        // Конфигурация сканера
        const config = {
          fps: 10, // Кадров в секунду
          qrbox: { width: 250, height: 250 }, // Размер области сканирования
          aspectRatio: 1.0,
          supportedScanTypes: [Html5Qrcode.SCAN_TYPE_CAMERA],
        };
        
        // Запускаем сканирование
        await qrCodeScanner.start(
          { facingMode: "environment" }, // Задняя камера
          config,
          (decodedText, decodedResult) => {
            // QR-код успешно отсканирован
            if (!isMounted || isScanningRef.current) return;
            
            isScanningRef.current = true;
            handleQRScanned(decodedText);
          },
          (errorMessage) => {
            // Ошибки сканирования игнорируем (это нормально во время поиска QR)
          }
        );
        
        setStatus("scanning");
      } catch (err) {
        console.error("Ошибка инициализации QR сканера:", err);
        
        let errorMessage = "Не удалось запустить сканер QR-кодов.";
        
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          errorMessage = "Доступ к камере запрещен. Разрешите доступ к камере в настройках браузера.";
        } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
          errorMessage = "Камера не найдена. Убедитесь, что камера подключена и работает.";
        } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
          if (err.message && err.message.toLowerCase().includes("device in use")) {
            errorMessage = "Камера уже используется другим приложением. Закройте другие приложения или вкладки, использующие камеру, и попробуйте снова.";
          } else {
            errorMessage = "Камера недоступна. Закройте другие приложения, использующие камеру.";
          }
        } else if (err.message) {
          errorMessage = err.message;
        }
        
        setError(errorMessage);
        setStatus("error");
      }
    };
    
    initializeQRScanner();
    
    return () => {
      isMounted = false;
      stopScanner();
    };
  }, []);

  const stopScanner = async () => {
    if (qrCodeScannerRef.current) {
      try {
        await qrCodeScannerRef.current.stop();
        await qrCodeScannerRef.current.clear();
      } catch (err) {
        console.error("Ошибка остановки сканера:", err);
      }
      qrCodeScannerRef.current = null;
    }
    isScanningRef.current = false;
  };


  const handleManualInput = (url) => {
    // Извлекаем user_code из URL
    try {
      const urlObj = new URL(url);
      const userCode = urlObj.searchParams.get("user_code");
      if (userCode) {
        // Редиректим на страницу верификации
        window.location.href = `/sso/qr/verify?user_code=${userCode}`;
      } else {
        setError("URL не содержит user_code. Убедитесь, что это правильный QR-код от платформы.");
      }
    } catch (err) {
      setError("Неверный формат URL. Введите правильную ссылку из QR-кода.");
    }
  };

  // Всегда рендерим интерфейс, но показываем загрузку если нужно

  if (status === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-100 to-red-300 p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Ошибка доступа к камере</h1>
          <p className="text-gray-700 mb-4">{error}</p>
          <div className="space-y-3">
            <button
              onClick={() => {
                setStatus("initializing");
                setError(null);
                isScanningRef.current = false;
                // Перезапускаем компонент
                window.location.reload();
              }}
              className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
            >
              Попробовать снова
            </button>
            <button
              onClick={() => setStatus("manual")}
              className="w-full bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300"
            >
              Ввести ссылку вручную
            </button>
            <button
              onClick={onCancel}
              className="w-full text-gray-600 hover:text-gray-800"
            >
              Отмена
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === "manual") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-300 p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold text-blue-700 mb-4">Ввести ссылку вручную</h1>
          <p className="text-gray-600 mb-4">
            Вставьте ссылку из QR-кода платформы:
          </p>
          <input
            type="text"
            placeholder="http://localhost:3000/sso/qr/verify?user_code=..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleManualInput(e.target.value);
              }
            }}
          />
          <div className="space-y-2">
            <button
              onClick={(e) => {
                const input = e.target.previousElementSibling;
                handleManualInput(input.value);
              }}
              className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
            >
              Открыть
            </button>
            <button
              onClick={() => setStatus("scanning")}
              className="w-full bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300"
            >
              Вернуться к сканеру
            </button>
            <button
              onClick={onCancel}
              className="w-full text-gray-600 hover:text-gray-800"
            >
              Отмена
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-black">
      {/* Заголовок */}
      <div className="bg-black text-white p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">Сканер QR-кода</h1>
        <button
          onClick={onCancel}
          className="text-white hover:text-gray-300"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Контейнер для QR сканера (html5-qrcode вставит сюда видео) */}
      <div className="flex-1 relative flex items-center justify-center bg-black">
        <div 
          ref={scannerContainerRef}
          className="w-full h-full"
          style={{ position: "relative" }}
        />
        
        {/* Индикатор загрузки поверх сканера */}
        {(status === "initializing" || status === "starting") && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 z-10">
            <div className="text-center">
              <div className="text-white font-medium mb-2">Инициализация сканера...</div>
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto"></div>
            </div>
          </div>
        )}
        
        {/* Инструкция */}
        {status === "scanning" && (
          <div className="absolute bottom-20 left-0 right-0 text-center z-10">
            <p className="text-white text-lg font-semibold bg-black bg-opacity-50 px-4 py-2 rounded-lg inline-block">
              Наведите камеру на QR-код
            </p>
          </div>
        )}
      </div>

      {/* Кнопки */}
      <div className="bg-black p-4 space-y-2">
        <button
          onClick={() => setStatus("manual")}
          className="w-full bg-gray-700 text-white py-2 rounded-lg hover:bg-gray-600"
        >
          Ввести ссылку вручную
        </button>
      </div>
    </div>
  );
}

