"""
Domain Models — Customer (SQLAlchemy 2.0).
Stores customer data (CRM Lite).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.order import Order


class Customer(Base):
    """
    A customer in the system. 
    Primary Key is document_id (DNI) as requested by the user.
    """
    __tablename__ = "customers"

    document_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    
    # Shipping data stored as JSONB
    # {
    #   "address": "...",
    #   "city": "...",
    #   "province": "...",
    #   "zip_code": "...",
    #   "department": "...",
    #   "district": "..."
    # }
    shipping_data: Mapped[dict | None] = mapped_column(JSONB)

    # ── Relationships ────────────────────────────────────────────────────────
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
