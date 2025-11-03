"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";

// Динамический импорт Webcam (только на клиенте)
const Webcam = dynamic(() => import("react-webcam"), { ssr: false });

// Динамический импорт face-api утилит
import { 
  loadModels, 
  detectFace, 
  drawFaceBox, 
  validateFaceQuality,
  formatDescriptorForServer,
  checkFaceOrientation
} from "../utils/faceApi";

export default function BiometricLogin({ onSuccess, onCancel }) {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const stableDetectionTimerRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  
  const [isModelsLoaded, setIsModelsLoaded] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [status, setStatus] = useState({ type: null, message: "" });
  const [faceDetected, setFaceDetected] = useState(false);
  const [orientationStatus, setOrientationStatus] = useState({ isLookingStraight: false, message: '' });
  const [countdown, setCountdown] = useState(null);
  const [loading, setLoading] = useState(false);

  // Загрузка моделей при монтировании компонента
  useEffect(() => {
    const initializeModels = async () => {
      setStatus({ type: "info", message: "Загрузка моделей распознавания..." });
      const loaded = await loadModels();
      
      if (loaded) {
        setIsModelsLoaded(true);
        setStatus({ type: "success", message: "Готово! Посмотрите прямо в камеру" });
      } else {
        setStatus({ type: "error", message: "Ошибка загрузки моделей" });
      }
    };

    initializeModels();
    
    // Очистка при размонтировании
    return () => {
      if (stableDetectionTimerRef.current) {
        clearTimeout(stableDetectionTimerRef.current);
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, []);

  // Детекция лица в реальном времени (каждые 300мс)
  useEffect(() => {
    if (!isModelsLoaded || isCapturing || loading) return;

    const detectInterval = setInterval(async () => {
      if (webcamRef.current && canvasRef.current) {
        const video = webcamRef.current.video;
        if (video && video.readyState === 4) {
          const detection = await detectFace(video);
          
          if (detection) {
            drawFaceBox(canvasRef.current, video, detection);
            setFaceDetected(true);
            
            // Проверяем ориентацию лица
            const orientation = checkFaceOrientation(detection);
            setOrientationStatus(orientation);
            
            // Если лицо смотрит прямо - запускаем таймер автоотправки
            if (orientation.isLookingStraight) {
              if (!stableDetectionTimerRef.current && !countdown) {
                startCountdown(detection);
              }
            } else {
              // Сбрасываем таймер если лицо отвернулось
              resetCountdown();
            }
          } else {
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

  // Запуск обратного отсчета
  const startCountdown = (detection) => {
    let count = 3;
    setCountdown(count);
    
    countdownIntervalRef.current = setInterval(() => {
      count--;
      setCountdown(count);
      
      if (count <= 0) {
        clearInterval(countdownIntervalRef.current);
        handleAutoCapture(detection);
      }
    }, 1000);
  };

  // Сброс обратного отсчета
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

  // Автоматический захват и отправка
  const handleAutoCapture = async (initialDetection) => {
    if (!webcamRef.current || isCapturing) return;

    setIsCapturing(true);
    setLoading(true);
    setCountdown(null);
    setStatus({ type: "info", message: "Распознавание лица..." });

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

      // Проверяем ориентацию еще раз
      const orientation = checkFaceOrientation(detection);
      if (!orientation.isLookingStraight) {
        setStatus({ type: "error", message: "Пожалуйста, смотрите прямо в камеру" });
        setIsCapturing(false);
        setLoading(false);
        return;
      }

      // Отправка на бэкенд для ВХОДА
      const response = await fetch('http://localhost:8000/biometric/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: formatDescriptorForServer(detection.descriptor)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Лицо не распознано');
      }

      // Успех! Передаем токены, данные пользователя и дескриптор
      setStatus({ type: "success", message: "Вход выполнен успешно!" });
      
      setTimeout(() => {
        onSuccess(
          data.user, 
          {
            access_token: data.access_token,
            refresh_token: data.refresh_token
          },
          detection.descriptor  // Передаем дескриптор для OAuth
        );
      }, 1000);

    } catch (err) {
      setStatus({ type: "error", message: err.message || 'Ошибка при входе' });
      setIsCapturing(false);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-100 to-purple-300 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 transition-all duration-300 text-center">
        <h1 className="text-3xl font-bold text-purple-700 mb-2">
          Вход по биометрии
        </h1>
        <p className="text-gray-600 text-sm mb-6">
          Посмотрите прямо в камеру
        </p>

        {!isModelsLoaded && (
          <div className="text-purple-600 mb-4 flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Загрузка моделей...
          </div>
        )}

        {isModelsLoaded && (
          <div className="relative w-full max-w-xs mx-auto mb-4">
            {/* Обратный отсчет - большая цифра поверх камеры */}
            {countdown !== null && countdown > 0 && (
              <div className="absolute inset-0 flex items-center justify-center z-10 bg-black bg-opacity-30 rounded-lg">
                <div className="text-white text-8xl font-bold animate-pulse">
                  {countdown}
                </div>
              </div>
            )}
            
            <Webcam
              audio={false}
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              width={320}
              height={240}
              className="rounded-lg shadow-md w-full"
              videoConstraints={{
                facingMode: "user"
              }}
            />
            <canvas
              ref={canvasRef}
              className="absolute top-0 left-0 w-full h-full"
            />
          </div>
        )}

        {/* Статус ориентации лица */}
        {isModelsLoaded && !loading && (
          <div className="mb-4">
            {faceDetected ? (
              <div className={`flex items-center justify-center gap-2 font-semibold ${
                orientationStatus.isLookingStraight ? 'text-green-600' : 'text-orange-600'
              }`}>
                {orientationStatus.isLookingStraight ? (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                )}
                <span className="text-sm">{orientationStatus.message}</span>
              </div>
            ) : (
              <span className="text-red-600 flex items-center justify-center gap-2">
                <svg className="w-5 h-5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                Лицо не обнаружено
              </span>
            )}
          </div>
        )}

        {/* Кнопка отмены */}
        <div className="space-y-4">
          <button
            onClick={onCancel}
            disabled={loading}
            className="w-full bg-gray-200 text-gray-700 font-semibold py-3 rounded-lg hover:bg-gray-300 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Отмена
          </button>
        </div>

        {/* Статусное сообщение */}
        {status.message && (
          <div
            className={`mt-6 p-4 rounded-lg text-center font-medium transition-all duration-300 ${
              status.type === "success"
                ? "bg-green-100 text-green-700 border border-green-300"
                : status.type === "error"
                ? "bg-red-100 text-red-700 border border-red-300"
                : "bg-blue-100 text-blue-700 border border-blue-300"
            }`}
          >
            {status.message}
          </div>
        )}

        {/* Инструкция */}
        {isModelsLoaded && !loading && (
          <div className="mt-4 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
            <p className="font-semibold mb-1">💡 Подсказка:</p>
            <p>Смотрите прямо в камеру. Вход произойдет автоматически через 3 секунды после обнаружения вашего лица.</p>
          </div>
        )}
      </div>
    </div>
  );
}
