"""Cấu hình ứng dụng (biến môi trường / backend/.env). Bí mật chỉ đến từ môi trường, không lưu trong DB."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sqlarena_app"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    app_timezone: str = "Asia/Ho_Chi_Minh"
    cors_origins: str = "http://localhost:5173"
    world_name: str = "enterprise_v1"          # world mà worker sinh/duyệt đề
    worker_poll_seconds: float = 3.0
    worker_id_prefix: str = "worker"
    seed_path: Path = BACKEND_DIR / "seed" / "core_seed.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
