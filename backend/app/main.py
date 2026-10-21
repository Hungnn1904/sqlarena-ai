"""FastAPI app: AI Pipeline & Question Management backend (prefix /api/v1 theo OpenAPI v7)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .errors import install_handlers
from .routers import admin, health, learner

app = FastAPI(title="SQLArena - AI Pipeline & Question Management", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
install_handlers(app)
app.include_router(health.router, prefix="/api/v1")
app.include_router(learner.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
