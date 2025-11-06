#!/usr/bin/env bash
set -euo pipefail

# Запуск бэкенда (FastAPI через uvicorn)
(
  cd "/app/life-backend"
  exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
) &
BACK_PID=$!

# Запуск фронтенда (Next.js)
(
  cd "/app/life"
  export NODE_ENV=production
  export PORT=${PORT:-3000}
  exec npm run start
) &
FRONT_PID=$!

# Ожидание завершения одного из процессов
wait -n "$BACK_PID" "$FRONT_PID"
exit $?





