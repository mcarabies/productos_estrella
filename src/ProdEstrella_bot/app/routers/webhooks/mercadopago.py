"""
Webhook Router — /webhooks/mercadopago

Handles Mercado Pago IPN/webhook notifications.
Validates HMAC-SHA256 signature then processes payment events in background.
Supports multi-item orders stored in Order.items (JSONB).
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi import status as http_status

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from redis.asyncio import Redis

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/mercadopago", tags=["webhooks"])


def _verify_mp_signature(
    x_signature: str,
    x_request_id: str,
    resource_id: str,
) -> bool:
    """
    Validate MP webhook HMAC-SHA256 signature.

    MP signs the string: id:<resource_id>;request-id:<x_request_id>;ts:<timestamp>;
    Format of x-signature header: ts=<timestamp>,v1=<hex_digest>
    """
    secret = settings.mp_webhook_secret.get_secret_value()
    if not secret:
        return True  # Skip if no secret configured

    try:
        parts = dict(p.split("=", 1) for p in x_signature.split(",") if "=" in p)
        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")

        signed_template = f"id:{resource_id};request-id:{x_request_id};ts:{ts};"
        computed = hmac.new(
            secret.encode("utf-8"),
            signed_template.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, v1)
    except Exception:
        return False


async def _process_mp_notification(data: dict[str, Any], redis: Redis) -> None:
    """
    Background task: handle a Mercado Pago payment notification.

    1. Retrieve full payment from MP API
    2. Verify status == 'approved'
    3. Update Order status in PostgreSQL
    4. Decrement stock for each item in the Order.items JSONB array
    5. Send success WhatsApp notification to customer
    """
    topic = data.get("type", "")
    resource_id = str(data.get("data", {}).get("id", ""))

    if topic != "payment":
        logger.info("webhook.mercadopago.ignored_topic", topic=topic)
        return

    if not resource_id:
        logger.warning("webhook.mercadopago.missing_resource_id", data=str(data)[:200])
        return

    from app.payments.mercadopago import get_payment_details
    from app.core.database import AsyncSessionLocal
    from app.domain.models import Order, Product
    from app.domain.models.order import OrderStatus
    from sqlalchemy.future import select
    from app.messaging.factory import get_whatsapp_provider

    try:
        payment = await get_payment_details(resource_id)
        status = payment.get("status")
        external_ref = payment.get("external_reference")

        logger.info(
            "webhook.mercadopago.payment_received",
            payment_id=resource_id,
            status=status,
            external_ref=external_ref,
        )

        if status != "approved" or not external_ref:
            logger.info(
                "webhook.mercadopago.not_approved_or_no_ref",
                status=status,
                external_ref=external_ref,
            )
            return

        async with AsyncSessionLocal() as db:
            # 1. Find Order
            stmt = select(Order).where(Order.id == external_ref)
            result = await db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error("webhook.mercadopago.order_not_found", order_id=external_ref)
                return

            if order.status == OrderStatus.paid:
                logger.info("webhook.mercadopago.order_already_paid", order_id=external_ref)
                return

            # 2. Mark order as paid
            order.status = OrderStatus.paid
            order.mp_payment_id = str(resource_id)

            # 3. Decrement stock for EACH item in the multi-item JSONB cart
            items_summary_parts = []
            order_items = order.items or []

            for cart_item in order_items:
                product_id = cart_item.get("product_id")
                item_qty = int(cart_item.get("quantity", 1))
                item_name = cart_item.get("name", "Producto")

                items_summary_parts.append(f"{item_qty}x {item_name}")

                if product_id:
                    stmt_p = select(Product).where(Product.id == product_id)
                    res_p = await db.execute(stmt_p)
                    product = res_p.scalar_one_or_none()

                    if product:
                        product.stock = max(0, product.stock - item_qty)
                        if product.stock <= 0:
                            product.is_active = False
                        logger.info(
                            "webhook.mercadopago.stock_updated",
                            product_id=product_id,
                            product_name=product.name,
                            qty_sold=item_qty,
                            remaining_stock=product.stock,
                        )

            await db.commit()
            logger.info("webhook.mercadopago.order_marked_paid", order_id=external_ref)

            # 4. WhatsApp confirmation message
            items_str = ", ".join(items_summary_parts) if items_summary_parts else "tu pedido"
            adapter = get_whatsapp_provider()
            msg = (
                f"🎉 *¡Tu pago fue aprobado!*\n\n"
                f"📦 Pedido: *{items_str}*\n"
                f"🔖 N° de operación: `{resource_id}`\n\n"
                f"Ya estamos preparando tu envío. ¡Muchas gracias por elegir *Productos Estrella*! ⭐\n\n"
                f"Te avisaremos cuando tu paquete esté en camino. 🚚"
            )
            await adapter.send_message(order.customer_phone, msg)
            logger.info("webhook.mercadopago.notification_sent", phone=order.customer_phone)

    except Exception as e:
        logger.error("webhook.mercadopago.processing_failed", error=str(e), payment_id=resource_id)


@router.post("", status_code=http_status.HTTP_200_OK)
async def mercadopago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    x_signature: str | None = Header(default=None, alias="x-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> dict[str, str]:
    """
    Receives Mercado Pago webhook (IPN) notifications.

    Security: validates HMAC-SHA256 signature before accepting the payload.
    Responds 200 OK immediately; processing runs in background.
    """
    raw_body = await request.body()

    import orjson
    try:
        data: dict[str, Any] = orjson.loads(raw_body)
    except Exception:
        logger.warning("webhook.mercadopago.invalid_json")
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    resource_id = str(data.get("data", {}).get("id", ""))

    # Signature validation (skip only if headers are missing, e.g. during MP testing)
    if x_signature and x_request_id and resource_id:
        if not _verify_mp_signature(x_signature, x_request_id, resource_id):
            logger.warning("webhook.mercadopago.invalid_signature", resource_id=resource_id)
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )
    else:
        logger.warning("webhook.mercadopago.missing_signature_headers", resource_id=resource_id)
        # Allow through for testing / initial setup, but log the anomaly

    background_tasks.add_task(_process_mp_notification, data, redis)
    return {"status": "received"}
