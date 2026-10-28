"""FastAPI app: AI Pipeline & Question Management (Hưng) + SQL Run & Leaderboard API (Đạt)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import install_handlers
from .routers import admin, auth, health, learner
import sql_run_api

app = FastAPI(title="SQLArena - Unified Backend (AI Pipeline & SQL Execution)", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
install_handlers(app)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(learner.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(sql_run_api.app.router)

