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
    enterprise_db_host: str = "localhost"
    enterprise_db_port: int = 5432
    enterprise_db_name: str = "enterprise_db"
    enterprise_db_user: str = "sqlarena_ai_ro"
    enterprise_db_password: str = "sqlarena_ro"
    catalog_db_host: str = "localhost"
    catalog_db_port: int = 5432
    catalog_db_name: str = "enterprise_db"
    catalog_db_user: str = ""
    catalog_db_password: str = ""
    statement_timeout_ms: int = 10000
    max_result_rows: int = 100000


@lru_cache
def get_settings() -> Settings:
    return Settings()
