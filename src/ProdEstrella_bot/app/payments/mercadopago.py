"""
Mercado Pago — SDK wrapper (Production-ready).

Follows the MercadoPago Quality Checklist requirements:
- items: id, title, description, category_id, unit_price, quantity
- payer: email, first_name, last_name, identification (DNI), phone, address
- preference: external_reference, notification_url, back_urls, auto_return,
              statement_descriptor, binary_mode
"""
from __future__ import annotations

import asyncio
from typing import Any

import mercadopago

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_mp_sdk() -> mercadopago.SDK:
    """Return an authenticated Mercado Pago SDK instance."""
    token = settings.mp_access_token.get_secret_value()
    return mercadopago.SDK(token)


async def create_preference(
    items: list[dict],
    payer_email: str,
    external_reference: str,
    # Extended payer data (from generar_link_de_pago tool)
    payer_name: str = "",
    payer_dni: str = "",
    payer_phone: str = "",
    shipping_address: str = "",
) -> dict[str, Any]:
    """
    Create a Mercado Pago Checkout Pro preference.

    Returns:
        dict with 'id' (preference_id) and 'init_point' (checkout URL).
    """
    sdk = get_mp_sdk()

    # ── Parse name into first/last ────────────────────────────────────────────
    name_parts = payer_name.strip().split(" ", 1)
    first_name = name_parts[0] if name_parts else "Cliente"
    last_name = name_parts[1] if len(name_parts) > 1 else "."

    # ── Enrich items with required MP fields ─────────────────────────────────
    enriched_items = []
    for i, item in enumerate(items):
        enriched_items.append({
            "id": item.get("product_id", str(i + 1)),
            "title": str(item["title"])[:256],
            "description": str(item.get("description", item["title"]))[:256],
            "category_id": "others",
            "unit_price": float(item["unit_price"]),
            "quantity": int(item["quantity"]),
            "currency_id": item.get("currency_id", "ARS"),
        })

    # ── Payer ─────────────────────────────────────────────────────────────────
    # NOTE: Only send the minimal required fields to avoid MP 400 errors.
    # The phone format (area_code must be int) and address fields can cause
    # schema validation failures in different MP environments.
    payer: dict[str, Any] = {
        "email": payer_email,
        "first_name": first_name,
        "last_name": last_name,
    }

    if payer_dni:
        payer["identification"] = {
            "type": "DNI",
            "number": str(payer_dni).strip(),
        }

    # ── Build preference payload ───────────────────────────────────────────────
    preference_data: dict[str, Any] = {
        "items": enriched_items,
        "payer": payer,
        "external_reference": external_reference,
        "notification_url": str(settings.mp_notification_url),
        "back_urls": {
            "success": f"https://{settings.app_domain}/payment/success",
            "failure": f"https://{settings.app_domain}/payment/failure",
            "pending": f"https://{settings.app_domain}/payment/pending",
        },
        "auto_return": "approved",
        "statement_descriptor": "PROD ESTRELLA",
        "binary_mode": True,  # Instant approval — no in-process states
    }

    logger.info(
        "mercadopago.creating_preference",
        external_ref=external_reference,
        item_count=len(enriched_items),
        payer_email=payer_email,
        payer_dni=payer_dni,
    )

    # Run the synchronous SDK in a thread to avoid blocking the event loop
    try:
        response = await asyncio.to_thread(sdk.preference().create, preference_data)
    except Exception as sdk_err:
        logger.error("mercadopago.sdk_exception", error=str(sdk_err))
        raise RuntimeError(f"MP SDK call failed: {sdk_err}") from sdk_err

    status = response.get("status")
    body = response.get("response", {})

    if status not in (200, 201):
        logger.error(
            "mercadopago.preference_creation_failed",
            http_status=status,
            mp_error_code=body.get("error"),
            mp_message=body.get("message"),
            mp_cause=body.get("cause"),
            mp_status=body.get("status"),
            full_response=str(body)[:500],
        )
        error_detail = body.get("message") or body.get("error") or str(body)
        raise RuntimeError(f"MP preference creation failed (HTTP {status}): {error_detail}")

    preference_id = body.get("id", "")
    init_point = body.get("init_point", "")

    logger.info(
        "mercadopago.preference_created",
        preference_id=preference_id,
        init_point=init_point,
    )

    return body


async def get_payment_details(payment_id: str) -> dict[str, Any]:
    """
    Retrieve full details of a payment from Mercado Pago API.
    Used by the webhook to verify payment approval.
    """
    sdk = get_mp_sdk()

    try:
        response = await asyncio.to_thread(sdk.payment().get, payment_id)
    except Exception as sdk_err:
        logger.error("mercadopago.get_payment_sdk_exception", error=str(sdk_err), payment_id=payment_id)
        raise RuntimeError(f"MP SDK call failed: {sdk_err}") from sdk_err

    status = response.get("status")
    body = response.get("response", {})

    if status != 200:
        logger.error(
            "mercadopago.payment_get_failed",
            http_status=status,
            payment_id=payment_id,
            mp_error=str(body)[:300],
        )
        raise RuntimeError(f"MP payment retrieval failed (HTTP {status}): {body}")

    return body
