#!/usr/bin/env bash
# Triển khai SQLArena AI trên VPS Linux / macOS qua IP trực tiếp (không cần tên miền).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

LKG_FILE="$ROOT_DIR/.deploy-lkg.sha"
BACKEND_PORT="${BACKEND_HOST_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_HOST_PORT:-3000}"
ADMIN_PORT="${ADMIN_HOST_PORT:-4000}"

detect_public_ip() {
  local ip=""
  if command -v curl >/dev/null 2>&1; then
    ip="$(curl -4 -fsS --max-time 2 https://api.ipify.org 2>/dev/null || true)"
  fi
  if [ -z "$ip" ] && command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi
  if [ -z "$ip" ] && command -v ifconfig >/dev/null 2>&1; then
    ip="$(ifconfig 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}' || true)"
  fi
  echo "${ip:-127.0.0.1}"
}

port_in_use() {
  local p="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tln 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${p}$"
    return $?
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

wait_http_ok() {
  local url="$1"
  local label="$2"
  local max_tries="${3:-45}"
  local i=1
  while [ "$i" -le "$max_tries" ]; do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
      echo "✅ $label sẵn sàng (200 OK): $url"
      return 0
    fi
    sleep 2
    i=$((i + 1))
  done
  echo "❌ $label không phản hồi sau $((max_tries * 2))s: $url" >&2
  return 1
}

case "${1:-deploy}" in
  --status|status)
    echo "📊 Trạng thái các container SQLArena AI:"
    docker compose ps
    echo ""
    curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" && echo "" || echo "⚠️ Backend healthcheck chưa phản hồi"
    exit 0
    ;;
  --rollback|rollback)
    if [ ! -f "$LKG_FILE" ]; then
      echo "❌ Chưa có bản lưu Last-Known-Good ($LKG_FILE) để rollback." >&2
      exit 1
    fi
    TARGET_SHA="$(cat "$LKG_FILE")"
    echo "⏪ Đang rollback về phiên bản ổn định trước đó ($TARGET_SHA)..."
    git checkout "$TARGET_SHA"
    docker compose up --build -d
    wait_http_ok "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" "Backend API"
    wait_http_ok "http://127.0.0.1:${FRONTEND_PORT}/" "Web Học viên"
    wait_http_ok "http://127.0.0.1:${ADMIN_PORT}/" "Web Quản trị"
    echo "✅ Rollback hoàn tất!"
    exit 0
    ;;
  --help|-h|help)
    echo "Cách dùng: ./scripts/deploy-vps.sh [deploy | --status | --rollback]"
    exit 0
    ;;
esac

echo "🚀 [SQLArena AI VPS Deploy] Bắt đầu kiểm tra môi trường..."

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Chưa cài đặt Docker trên VPS." >&2
  exit 1
fi

# Lưu SHA hiện tại làm điểm khôi phục LKG nếu có git repo
if command -v git >/dev/null 2>&1 && git rev-parse --verify HEAD >/dev/null 2>&1; then
  git rev-parse HEAD > "$LKG_FILE"
fi

# Tự phát hiện xung đột cổng 5432 / 8000 / 3000 với tiến trình khác trên máy chủ
if [ -z "${POSTGRES_HOST_PORT:-}" ]; then
  if port_in_use 5432 && ! docker ps --filter "name=^sqlarena-postgres$" --filter "publish=5432" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-postgres'; then
    export POSTGRES_HOST_PORT=5433
    echo "👉 Cổng 5432 đang được ứng dụng khác dùng — tự động chuyển Postgres container sang 127.0.0.1:5433."
  else
    export POSTGRES_HOST_PORT=5432
  fi
fi
if [ -z "${BACKEND_HOST_PORT:-}" ] && port_in_use 8000 && ! docker ps --filter "name=^sqlarena-backend$" --filter "publish=8000" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-backend'; then
  export BACKEND_HOST_PORT=8005
  BACKEND_PORT=8005
  echo "👉 Cổng 8000 đang được ứng dụng khác dùng — tự động chuyển Backend sang cổng 8005."
fi
if [ -z "${FRONTEND_HOST_PORT:-}" ] && port_in_use 3000 && ! docker ps --filter "name=^sqlarena-frontend$" --filter "publish=3000" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-frontend'; then
  export FRONTEND_HOST_PORT=3005
  FRONTEND_PORT=3005
  echo "👉 Cổng 3000 đang được ứng dụng khác dùng — tự động chuyển Web Học viên sang cổng 3005."
fi
if [ -z "${ADMIN_HOST_PORT:-}" ] && port_in_use 4000 && ! docker ps --filter "name=^sqlarena-frontend$" --filter "publish=4000" --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-frontend'; then
  export ADMIN_HOST_PORT=4005
  ADMIN_PORT=4005
  echo "👉 Cổng 4000 đang được ứng dụng khác dùng — tự động chuyển Web Quản trị sang cổng 4005."
fi

# Mặc định để trống NEXT_PUBLIC_API_URL để truy cập qua IP VPS không cần domain
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-}"

# Nếu đường dẫn thư mục chứa ký tự tiếng Việt (Unicode), tắt BuildKit gRPC để tránh lỗi header ASCII của Docker
if printf '%s' "$ROOT_DIR" | LC_ALL=C grep -q '[^ -~]'; then
  export DOCKER_BUILDKIT=0
  export COMPOSE_DOCKER_CLI_BUILD=0
fi

echo "🐳 Đang build & khởi chạy cụm container SQLArena AI..."
docker compose up --build -d

wait_http_ok "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" "Backend API (/api/v1/health)" 60
wait_http_ok "http://127.0.0.1:${FRONTEND_PORT}/" "Web Học viên (:${FRONTEND_PORT})" 45
wait_http_ok "http://127.0.0.1:${ADMIN_PORT}/" "Web Quản trị (:${ADMIN_PORT})" 45

VPS_IP="$(detect_public_ip)"
echo ""
echo "=================================================================="
echo "🎉 TRIỂN KHAI SQLARENA AI THÀNH CÔNG (KHÔNG CẦN DOMAIN)!"
echo "   🌐 Web Học viên:  http://${VPS_IP}:${FRONTEND_PORT}"
echo "   🛠️ Web Quản trị:  http://${VPS_IP}:${ADMIN_PORT}"
echo "   🔌 Backend Swagger Docs:            http://${VPS_IP}:${BACKEND_PORT}/api/docs"
echo "   🔒 PostgreSQL nội bộ an toàn:       127.0.0.1:${POSTGRES_HOST_PORT}"
echo "   📊 Kiểm tra trạng thái:             ./scripts/deploy-vps.sh --status"
echo "   ⏪ Khôi phục bản trước (Rollback):  ./scripts/deploy-vps.sh --rollback"
echo "=================================================================="
