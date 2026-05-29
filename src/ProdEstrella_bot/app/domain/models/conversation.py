"""
Domain Models — Conversation (SQLAlchemy 2.0).
Tracks the AI conversation stage and thread ID per customer phone.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConversationStage(StrEnum):
    intake = "intake"            # Greeting, presenting product
    negotiation = "negotiation"  # Stage 2: Gemini Flash
    closing = "closing"          # Stage 3: Gemini Pro
    completed = "completed"      # Order placed
    inactive = "inactive"        # Timed out / abandoned


class Conversation(Base):
    """
    Tracks the current AI conversation state for a customer phone number.

    The actual message history lives in Redis (compressed, TTL 24h).
    This table holds only durable metadata and the stage pointer.
    """
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_phone: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ConversationStage.intake
    )
    # Redis key where the message history is stored
    redis_thread_key: Mapped[str | None] = mapped_column(String(200))
    # Number of turns so far (for analytics / guardrails)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
