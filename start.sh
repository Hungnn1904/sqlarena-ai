#!/usr/bin/env bash
set -e

MODE="${1:---local}"

if [ "$MODE" = "--docker" ]; then
  echo "🐳 [SQLArena AI] Đang khởi động toàn bộ hệ thống qua Docker Compose..."
  echo "👉 Nếu PostgreSQL 17 trên máy Mac đang chiếm cổng 5432, Docker sẽ tự động dùng cổng 5433 cho Postgres container."
  if lsof -i :5432 >/dev/null 2>&1; then
    export POSTGRES_HOST_PORT=5433
  fi
  docker compose up --build -d
  echo "✅ Đã bật Docker Compose thành công!"
  echo "   🌐 Frontend Next.js 16: http://127.0.0.1:${FRONTEND_HOST_PORT:-3000}"
  echo "   🔌 Backend FastAPI:     http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/api/docs"
  exit 0
fi

echo "⚡ [SQLArena AI] Đang kiểm tra & khởi chạy chế độ Local Native siêu tốc..."
cd "$(dirname "$0")"

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
