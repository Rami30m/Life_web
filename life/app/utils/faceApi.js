import * as faceapi from 'face-api.js';

let modelsLoaded = false;

/**
 * Загрузка моделей face-api.js
 * Модели загружаются один раз при первом вызове
 */
export const loadModels = async () => {
  if (modelsLoaded) {
    console.log('✅ Модели уже загружены');
    return true;
  }

  try {
    console.log('📦 Загрузка моделей face-api.js...');
    
    const MODEL_URL = '/models';
    
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]);

    modelsLoaded = true;
    console.log('✅ Модели успешно загружены');
    return true;
  } catch (error) {
    console.error('❌ Ошибка загрузки моделей:', error);
    return false;
  }
};

/**
 * Детекция лица и извлечение дескрипторов
 * @param {HTMLVideoElement|HTMLImageElement} input - Видео или изображение
 * @returns {Promise<Object|null>} - Объект с дескрипторами или null
 */
export const detectFace = async (input) => {
  try {
    // Используем tiny face detector для скорости
    const detections = await faceapi
      .detectSingleFace(input, new faceapi.TinyFaceDetectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptor();

    if (!detections) {
      return null;
    }

    return {
      detection: detections.detection,
      landmarks: detections.landmarks,
      descriptor: Array.from(detections.descriptor), // Преобразуем Float32Array в обычный массив
      confidence: detections.detection.score,
    };
  } catch (error) {
    console.error('❌ Ошибка детекции лица:', error);
    return null;
  }
};

/**
 * Рисует рамку вокруг обнаруженного лица на canvas
 * @param {HTMLCanvasElement} canvas - Canvas для рисования
 * @param {HTMLVideoElement} video - Видео элемент (не используется, для совместимости)
 * @param {Object} detection - Результат детекции от face-api
 */
export const drawFaceBox = (canvas, video, detection) => {
  if (!canvas || !detection) return;
  
  const ctx = canvas.getContext('2d');
  const box = detection.detection.box;
  
  // Очищаем canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Рисуем рамку
  ctx.strokeStyle = '#00ff00';
  ctx.lineWidth = 3;
  ctx.strokeRect(box.x, box.y, box.width, box.height);
  
  // Рисуем точки landmarks (зеленые точки!)
  if (detection.landmarks) {
    ctx.fillStyle = '#00ff00';
    detection.landmarks.positions.forEach((point) => {
      ctx.beginPath();
      ctx.arc(point.x, point.y, 2, 0, 2 * Math.PI);
      ctx.fill();
    });
  }
  
  // Показываем уверенность
  const confidence = Math.round(detection.detection.score * 100);
  ctx.fillStyle = '#00ff00';
  ctx.font = 'bold 16px Arial';
  ctx.fillText(`${confidence}%`, box.x, box.y - 10);
};

/**
 * Проверка качества детекции
 * @param {Object} detection - Результат детекции
 * @returns {Object} - Результат проверки {valid: boolean, message: string}
 */
export const validateFaceQuality = (detection) => {
  if (!detection) {
    return {
      valid: false,
      message: 'Лицо не обнаружено. Пожалуйста, посмотрите в камеру.'
    };
  }

  // Проверяем уверенность детекции
  if (detection.confidence < 0.5) {
    return {
      valid: false,
      message: 'Качество изображения низкое. Улучшите освещение.'
    };
  }

  // Проверяем размер лица (не слишком далеко)
  const box = detection.detection.box;
  if (box.width < 100 || box.height < 100) {
    return {
      valid: false,
      message: 'Подойдите ближе к камере.'
    };
  }

  return {
    valid: true,
    message: 'Лицо успешно обнаружено!'
  };
};

/**
 * Проверка ориентации лица (смотрит ли прямо в камеру)
 * @param {Object} detection - Результат детекции с landmarks
 * @returns {Object} - {isLookingStraight: boolean, message: string, angles: {yaw, pitch, roll}}
 */
export const checkFaceOrientation = (detection) => {
  if (!detection || !detection.landmarks) {
    return {
      isLookingStraight: false,
      message: 'Лицо не обнаружено',
      angles: null
    };
  }

  try {
    const landmarks = detection.landmarks.positions;
    
    // Проверяем что landmarks массив достаточно большой
    if (!landmarks || landmarks.length < 68) {
      console.warn('Недостаточно landmarks точек:', landmarks?.length);
      // Если нет landmarks - считаем что лицо смотрит прямо (не блокируем)
      return {
        isLookingStraight: true,
        message: 'Лицо обнаружено',
        angles: null
      };
    }
    
    // Ключевые точки лица:
    // 36-41: Левый глаз, 42-47: Правый глаз
    // 30: Кончик носа, 27: Переносица
    const leftEye = landmarks[36];  // Левый глаз (внешний угол)
    const rightEye = landmarks[45]; // Правый глаз (внешний угол)
    const nose = landmarks[30];     // Кончик носа
    
    if (!leftEye || !rightEye || !nose) {
      console.warn('Не найдены ключевые точки лица');
      return {
        isLookingStraight: true,
        message: 'Лицо обнаружено',
        angles: null
      };
    }
    
    // Вычисляем расстояние между глазами
    const eyeDistance = Math.sqrt(
      Math.pow(rightEye.x - leftEye.x, 2) + 
      Math.pow(rightEye.y - leftEye.y, 2)
    );
    
    // Центр между глазами
    const eyeCenter = {
      x: (leftEye.x + rightEye.x) / 2,
      y: (leftEye.y + rightEye.y) / 2
    };
    
    // Проверяем горизонтальное отклонение носа от центра (Yaw - поворот головы влево/вправо)
    const horizontalOffset = Math.abs(nose.x - eyeCenter.x);
    const horizontalThreshold = eyeDistance * 0.2; // 20% (было 15%, делаю мягче)
    
    // Проверяем вертикальное положение (Pitch - наклон вверх/вниз)
    const verticalOffset = Math.abs(nose.y - eyeCenter.y);
    const verticalThreshold = eyeDistance * 0.4; // 40% (было 30%, делаю мягче)
    
    // Проверяем наклон головы (Roll - поворот головы по оси)
    const eyeAngle = Math.abs(Math.atan2(rightEye.y - leftEye.y, rightEye.x - leftEye.x) * (180 / Math.PI));
    const rollThreshold = 20; // 20 градусов (было 15, делаю мягче)
    
    const isLookingStraight = 
      horizontalOffset < horizontalThreshold && 
      verticalOffset < verticalThreshold && 
      eyeAngle < rollThreshold;
    
    let message = '';
    if (horizontalOffset >= horizontalThreshold) {
      message = nose.x < eyeCenter.x 
        ? 'Поверните голову немного вправо' 
        : 'Поверните голову немного влево';
    } else if (verticalOffset >= verticalThreshold) {
      message = nose.y < eyeCenter.y 
        ? 'Поднимите голову немного вверх' 
        : 'Опустите голову немного вниз';
    } else if (eyeAngle >= rollThreshold) {
      message = 'Выровняйте голову (не наклоняйте)';
    } else {
      message = 'Отлично! Держите так';
    }
    
    return {
      isLookingStraight,
      message,
      angles: {
        yaw: horizontalOffset / horizontalThreshold,
        pitch: verticalOffset / verticalThreshold,
        roll: eyeAngle / rollThreshold
      }
    };
  } catch (error) {
    console.error('Ошибка в checkFaceOrientation:', error);
    // При ошибке не блокируем - возвращаем что лицо найдено
    return {
      isLookingStraight: true,
      message: 'Лицо обнаружено',
      angles: null
    };
  }
};

/**
 * Сравнение двух дескрипторов лиц (для будущего использования)
 * @param {Array} descriptor1 - Первый дескриптор
 * @param {Array} descriptor2 - Второй дескриптор
 * @returns {number} - Расстояние между дескрипторами (чем меньше, тем больше похожи)
 */
export const compareFaces = (descriptor1, descriptor2) => {
  const d1 = new Float32Array(descriptor1);
  const d2 = new Float32Array(descriptor2);
  return faceapi.euclideanDistance(d1, d2);
};

/**
 * Форматирование дескриптора для отправки на сервер
 * @param {Array} descriptor - Дескриптор лица
 * @returns {string} - JSON строка с дескриптором
 */
export const formatDescriptorForServer = (descriptor) => {
  return JSON.stringify({
    descriptor: descriptor,
    timestamp: new Date().toISOString(),
    version: '1.0'
  });
};

