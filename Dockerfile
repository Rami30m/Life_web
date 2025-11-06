# Мультистейдж: сначала билд фронтенда, затем финальный рантайм с Node+Python

# 1) Сборка фронтенда (Next.js)
FROM node:18-bullseye AS frontend-build
WORKDIR /app/life

# Устанавливаем зависимости фронтенда
COPY life/package.json life/package-lock.json ./
RUN npm install --no-audit --no-fund

# Копируем остальной фронтенд и собираем
COPY life/ ./
RUN npm run build


# 2) Финальный образ: Node + Python (для Next.js и FastAPI)
FROM node:18-bullseye AS runtime

# Устанавливаем Python и pip
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Бэкенд ---
# Сначала устанавливаем зависимости бэкенда
COPY ["Life back2/requirements.txt", "/app/life-backend/requirements.txt"]
RUN pip3 install --no-cache-dir -r /app/life-backend/requirements.txt

# Теперь копируем исходники бэкенда
COPY ["Life back2/", "/app/life-backend/"]

# --- Фронтенд ---
WORKDIR /app/life
# Устанавливаем только прод-зависимости фронтенда
COPY life/package.json life/package-lock.json ./
RUN npm install --omit=dev --no-audit --no-fund

# Копируем результаты сборки и необходимые файлы
COPY --from=frontend-build /app/life/.next ./.next
COPY --from=frontend-build /app/life/public ./public
COPY life/next.config.mjs ./next.config.mjs
COPY life/app ./app

WORKDIR /app

# Скрипт запуска
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV PORT=3000
EXPOSE 3000 8000

CMD ["/bin/bash", "/app/start.sh"]


