#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
MODE="${1:---local}"

if [ "$MODE" = "--vps" ]; then
  shift || true
  exec ./scripts/deploy-vps.sh "$@"
fi

if [ "$MODE" = "--docker" ]; then
  echo "🐳 [SQLArena AI] Đang khởi động toàn bộ hệ thống qua Docker Compose..."
  if printf '%s' "$PWD" | LC_ALL=C grep -q '[^ -~]'; then
    export DOCKER_BUILDKIT=0
    export COMPOSE_DOCKER_CLI_BUILD=0
  fi
  if lsof -i :5432 >/dev/null 2>&1 && ! docker ps --filter "name=^sqlarena-postgres$" --filter "publish=5432" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-postgres'; then
    echo "👉 Phát hiện cổng 5432 đang bận trên máy chủ, tự động gán POSTGRES_HOST_PORT=5433."
    export POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-5433}"
  fi
  if lsof -i :3000 >/dev/null 2>&1 && ! docker ps --filter "name=^sqlarena-frontend$" --filter "publish=3000" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-frontend'; then
    echo "👉 Phát hiện cổng 3000 đang bận trên máy chủ, tự động gán FRONTEND_HOST_PORT=3005."
    export FRONTEND_HOST_PORT="${FRONTEND_HOST_PORT:-3005}"
  fi
  if lsof -i :4000 >/dev/null 2>&1 && ! docker ps --filter "name=^sqlarena-frontend$" --filter "publish=4000" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-frontend'; then
    echo "👉 Phát hiện cổng 4000 đang bận trên máy chủ, tự động gán ADMIN_HOST_PORT=4005."
    export ADMIN_HOST_PORT="${ADMIN_HOST_PORT:-4005}"
  fi
  docker compose up --build -d
  FRONTEND_PORT="${FRONTEND_HOST_PORT:-3000}"
  ADMIN_PORT="${ADMIN_HOST_PORT:-4000}"
  for i in $(seq 1 30); do
    if curl -fsS --max-time 2 "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1 && \
       curl -fsS --max-time 2 "http://127.0.0.1:${ADMIN_PORT}/" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  echo "✅ Đã bật Docker Compose thành công!"
  echo "   🌐 Giao diện Web thống nhất: http://127.0.0.1:${FRONTEND_PORT} (/ , /progress , /leaderboard , /admin)"
  echo "   🔌 Backend FastAPI:          http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/api/docs"
  exit 0
fi

echo "⚡ [SQLArena AI] Đang kiểm tra & khởi chạy chế độ Local Native siêu tốc..."

# 1. Migrate & Seed Demo Data
(cd backend && ../.venv/bin/python -m app.cli migrate && ../.venv/bin/python -m app.cli seed-demo)

# 2. Start Backend on 8000 if not already listening
if ! lsof -i :8000 >/dev/null 2>&1; then
  (cd backend && nohup ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/sqlarena-backend.log 2>&1 &)
  echo "✓ Đã bật FastAPI Backend tại http://127.0.0.1:8000"
else
  echo "✓ FastAPI Backend đang chạy sẵn tại http://127.0.0.1:8000"
fi

# 3. Start Next.js Frontend on 3000 if not already listening
if ! lsof -i :3000 >/dev/null 2>&1; then
  (cd frontend && nohup npm run dev -- -p 3000 -H 127.0.0.1 > /tmp/sqlarena-frontend.log 2>&1 &)
  echo "✓ Đã bật Next.js 16 Frontend tại http://127.0.0.1:3000"
else
  echo "✓ Next.js 16 Frontend đang chạy sẵn tại http://127.0.0.1:3000"
fi

# 4. Start Legacy learner.html on 5500 if not already listening
if ! lsof -i :5500 >/dev/null 2>&1; then
  (nohup python3 -m http.server 5500 --bind 127.0.0.1 > /tmp/sqlarena-html.log 2>&1 &)
  echo "✓ Đã bật Legacy learner.html tại http://127.0.0.1:5500/learner.html"
else
  echo "✓ Legacy learner.html đang chạy sẵn tại http://127.0.0.1:5500/learner.html"
fi

echo ""
echo "🎉 Toàn bộ hệ thống đã sẵn sàng:"
echo "   👉 Giao diện chính (Next.js 16): http://127.0.0.1:3000"
echo "   👉 Giao diện cũ (learner.html):  http://127.0.0.1:5500/learner.html"
echo "   👉 Tài liệu API (Swagger):       http://127.0.0.1:8000/api/docs"
