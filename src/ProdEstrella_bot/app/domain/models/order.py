"""
Domain Models — Order (SQLAlchemy 2.0 declarative style, async-ready).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(StrEnum):
    pending_payment = "pending_payment"
    paid = "paid"
    in_preparation = "in_preparation"
    cancelled = "cancelled"
    shipped = "shipped"
    delivered = "delivered"
    refunded = "refunded"


class Order(Base):
    """Represents a customer purchase order."""
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_dni: Mapped[str] = mapped_column(
        String(20), ForeignKey("customers.document_id"), nullable=False, index=True
    )
    # Legacy single product (nullable for backward compatibility or direct single purchases)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    
    # NEW: Multi-item cart support
    items: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, server_default='[]')
    
    # We keep phone for quick access as well, but linked to customer
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=OrderStatus.pending_payment, index=True
    )
    # MP payment reference
    mp_preference_id: Mapped[str | None] = mapped_column(String(200), index=True)
    mp_payment_id: Mapped[str | None] = mapped_column(String(200))
    
    # Order total
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    
    # Notes (AI chain of thought, customer notes, etc.)
    notes: Mapped[str | None] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────────
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders", lazy="selectin")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
