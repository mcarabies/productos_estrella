"""
FastAPI application factory — entry point.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger
from app.core.redis_client import get_redis_client, close_redis
from starlette.middleware.sessions import SessionMiddleware
from app.routers.webhooks import mercadopago as mp_router
from app.routers.webhooks import whatsapp as wa_router
from app.routers.admin import auth as auth_router
from app.routers.admin import dashboard as dashboard_router
from app.routers.public import redirect as redirect_router

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup/shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info(
        "app.startup",
        env=settings.app_env,
        provider=settings.whatsapp_provider,
        ai_stage1=settings.ai_stage1_model,
        ai_stage2=settings.ai_stage2_model,
        ai_stage3=settings.ai_stage3_model,
    )

    # Warm up Redis connection pool
    await get_redis_client()
    logger.info("app.redis_connected")

    # Verify DB connectivity (asyncpg will raise if DB unreachable)
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    logger.info("app.database_connected")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await close_redis()
    await engine.dispose()
    logger.info("app.shutdown")


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="ProdEstrella Sales Bot API",
        description="WhatsApp Dropshipping Sales Bot — AI-driven, async backend",
        version="0.1.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
        openapi_url="/openapi.json" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # ── Middlewares ───────────────────────────────────────────────────────────
    app.add_middleware(
        SessionMiddleware, secret_key=settings.app_secret_key.get_secret_value(), max_age=86400
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten per-domain in Phase 2
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # ── Static Files ──────────────────────────────────────────────────────────
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(wa_router.router)
    app.include_router(mp_router.router)
    app.include_router(auth_router.router)
    app.include_router(dashboard_router.router)
    app.include_router(redirect_router.router)

    # ── Health check ─────────────────────────────────────────────────────────
    @app.get("/health", tags=["system"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/", tags=["system"], include_in_schema=False)
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/admin/login", status_code=302)

    return app


app = create_app()
