"""
Domain Model — ShortLink.
Stores short URL codes that redirect to full wa.me links.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ShortLink(Base):
    """
    A short link entry that maps a compact code to a full destination URL.

    Example:
        code         = "pBx3Kq"
        destination  = "https://wa.me/5491122334455?text=..."
        short_url    = "https://api.productosestrella.club/r/pBx3Kq"
    """
    __tablename__ = "short_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The short alphanumeric code (e.g. "pBx3Kq")
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    # The full destination URL (the wa.me link)
    destination: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
