"""
App configuration — Pydantic Settings v2.
Reads from environment variables / .env file.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import AnyHttpUrl, Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    development = "development"
    production = "production"


class WhatsAppProvider(StrEnum):
    evolution = "evolution"
    meta = "meta"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_env: Environment = Environment.production
    app_debug: bool = False
    app_secret_key: SecretStr = Field(..., min_length=32)
    log_level: str = "INFO"
    
    # ── Admin Credentials ──────────────────────────────────────────────────────
    admin_username: str = "mcarabies"
    admin_password: SecretStr = SecretStr("29232436mjC**")

    # ── Domains ────────────────────────────────────────────────────────────────
    app_domain: str = "api.productosestrella.club"
    evo_domain: str = "wsp.productosestrella.club"
    # Domain used in public-facing short links (e.g. product.productosestrella.club)
    link_domain: str = "product.productosestrella.club"

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str  # postgresql+asyncpg://...
    postgres_user: str = "prodEstrella_user"
    postgres_password: SecretStr = Field(...)
    postgres_db: str = "prodEstrella_db"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str  # redis://:password@host:port/db
    redis_session_ttl: int = 86_400  # 24 hours in seconds

    # ── WhatsApp Provider ─────────────────────────────────────────────────────
    whatsapp_provider: WhatsAppProvider = WhatsAppProvider.evolution
    bot_phone_number: str = "" # e.g. 5491122334455

    # Evolution API
    evolution_api_url: AnyHttpUrl = AnyHttpUrl("http://evolution:8080")
    evolution_api_key: SecretStr = Field(...)
    evolution_instance_name: str = "prodEstrella-bot"
    evolution_typing_min: float = 1.0
    evolution_typing_max: float = 3.5

    # Meta Cloud API
    meta_phone_number_id: str = ""
    meta_whatsapp_token: SecretStr = SecretStr("")
    meta_webhook_verify_token: SecretStr = SecretStr("")
    meta_app_secret: SecretStr = SecretStr("")

    # ── Mercado Pago ──────────────────────────────────────────────────────────
    mp_access_token: SecretStr = Field(...)
    mp_public_key: str = ""
    mp_webhook_secret: SecretStr = Field(...)
    mp_notification_url: AnyHttpUrl = AnyHttpUrl(
        "https://api.productosestrella.club/webhooks/mercadopago"
    )

    # ── Google AI (Gemini) ────────────────────────────────────────────────────
    google_api_key: SecretStr = Field(...)
    ai_stage1_model: str = Field(default="gemini-3.1-pro-preview")         # Admin / ingestion (slow, deep reasoning)
    ai_stage2_model: str = Field(default="gemini-3.1-flash-lite-preview")  # Negotiation (ultra fast for chatting)
    ai_stage3_model: str = Field(default="gemini-3.1-pro-preview")         # Closing (high precision for structured data extraction)


# Singleton — imported throughout the app
settings = Settings()  # type: ignore[call-arg]
