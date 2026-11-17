#!/usr/bin/env bash
# Secret-Blind AK-Vault Key Provisioner cho https://apithat.dev/keys (không in khóa ra màn hình/lịch sử).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODEL_CHOICE="${1:-gpt-5.6-sol}"
BASE_URL="${APITHAT_BASE_URL:-https://apithat.dev/v1}"

printf "🔑 Dán APITHAT_API_KEY lấy từ https://apithat.dev/keys (ký tự được ẩn bảo mật): "
read -rs INPUT_KEY
echo ""

INPUT_KEY="$(printf '%s' "$INPUT_KEY" | tr -d '\r\n ')"
if [ "${#INPUT_KEY}" -lt 12 ]; then
  echo "❌ Khóa API quá ngắn hoặc đang để trống." >&2
  exit 1
fi

HTTP_CODE="$(curl -sS -o /tmp/apithat_probe.json -w '%{http_code}' \
  -H "Authorization: Bearer ${INPUT_KEY}" \
  -H "User-Agent: SQLArena-AI/2.0" \
  "${BASE_URL%/}/models" || echo "000")"
rm -f /tmp/apithat_probe.json

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Khóa API bị từ chối bởi ${BASE_URL%/}/models (HTTP ${HTTP_CODE}). Kiểm tra lại khóa trên https://apithat.dev/keys." >&2
  exit 1
fi

upsert_kv() {
  local file="$1" key="$2" val="$3"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  chmod 600 "$file"
  python3 - "$file" "$key" "$val" <<'PY'
import pathlib, sys
p, k, v = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
out, found = [], False
for ln in lines:
    s = ln.strip()
    if s and not s.startswith("#") and s.split("=", 1)[0].strip() == k:
        out.append(f"{k}={v}")
        found = True
    else:
        out.append(ln)
if not found:
    out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n", encoding="utf-8")
PY
}

for target in "$HOME/.mykit/vault.env" "$ROOT_DIR/.env" "$ROOT_DIR/backend/.env"; do
  upsert_kv "$target" "APITHAT_API_KEY" "$INPUT_KEY"
  upsert_kv "$target" "APITHAT_BASE_URL" "$BASE_URL"
  upsert_kv "$target" "APITHAT_MODEL" "$MODEL_CHOICE"
done

MASKED="${INPUT_KEY:0:4}...${INPUT_KEY: -4}"
echo "✅ Đã xác thực 200 OK và lưu Secret-Blind (${MASKED}) vào ~/.mykit/vault.env, .env, backend/.env (chmod 600)."

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'sqlarena-backend'; then
  echo "🔄 Đang nạp lại cấu hình cho sqlarena-backend & sqlarena-worker..."
  ./scripts/deploy-vps.sh
fi
