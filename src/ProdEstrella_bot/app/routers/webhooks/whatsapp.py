"""
Webhook Router — /webhooks/whatsapp

Handles inbound messages from BOTH Evolution API and Meta Cloud API.
The key rule: respond HTTP 200 OK IMMEDIATELY, then process in background.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi import status as http_status

from app.core.config import WhatsAppProvider, settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from redis.asyncio import Redis

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


async def _process_whatsapp_message(
    payload: dict[str, Any],
    redis: Redis,
) -> None:
    """
    Background task: parse the inbound message and hand off to the AI pipeline.
    """
    provider = settings.whatsapp_provider
    logger.info("webhook.whatsapp.payload_received", provider=provider, webhook_event=payload.get("event"))

    phone = ""
    text = ""

    if provider == WhatsAppProvider.evolution:
        event = payload.get("event")
        if not event or event.lower() != "messages.upsert":
            logger.info("webhook.evolution.ignored", reason="Event not messages.upsert", webhook_event=event)
            return  # Only process new messages
            
        data = payload.get("data", {})
        
        # Evolution structure varies: sometimes 'key' is inside 'data', sometimes inside 'data.message'
        key = data.get("key")
        if not key:
            nested_msg = data.get("message", {})
            key = nested_msg.get("key", {})
            
        if not key:
            logger.info("webhook.evolution.parse_failed", reason="no key found", data=data)
            return

        if key.get("fromMe") is True:
            logger.info("webhook.evolution.ignored", reason="fromMe is True", key=key)
            return  # Ignore messages sent by the bot itself
            
        remote_jid = key.get("remoteJid", "")
        if "@g.us" in remote_jid or "status" in remote_jid:
            logger.info("webhook.evolution.ignored", reason="group or status", remote_jid=remote_jid)
            return  # Ignore groups and status updates

        # Deduplication using Redis to solve the 'bot responding twice' issue.
        msg_id = key.get("id")
        if msg_id:
            already_processed = await redis.get(f"mp:{msg_id}")
            if already_processed:
                logger.info("webhook.evolution.deduped", msg_id=msg_id)
                return
            await redis.set(f"mp:{msg_id}", "1", ex=3600)  # expires in 1 hour
            
        phone = remote_jid.split("@")[0]
        
        # Extract text: look in data.message.conversation, data.message.extendedTextMessage, etc.
        msg_body = data.get("message", {})
        if not msg_body and "message" in data.get("message", {}):
            msg_body = data["message"]["message"]

        text = msg_body.get("conversation") or msg_body.get("extendedTextMessage", {}).get("text")
        
        if not text:
            # Maybe it's an image payload? For now we just log and return
            logger.info("webhook.evolution.no_text_found", msg_body=msg_body)
            return

    if not phone or not text:
        logger.info("webhook.evolution.empty_fields", phone=phone, text=text)
        return

    # ── Context Extraction ───────────────────────────────────────────────────
    import re
    from app.core.session import ChatSessionManager
    
    session_mgr = ChatSessionManager(redis)
    
    # Example format: "...\nRef: f54a..." UUID
    match = re.search(r"Ref:\s*([a-f0-9\-]{36})", text, re.IGNORECASE)
    if not match:
        # Fallback to the old format just in case
        match = re.search(r"me interesa el producto\s+([a-f0-9\-]{36})", text, re.IGNORECASE)
        
    if match:
        product_id = match.group(1).strip()
        logger.info("webhook.lead_context.detected", product_id=product_id, phone=phone)
        await session_mgr.update_state(phone, {"context_product_id": product_id})

    # 1. Fetch or create Conversation state from PostgreSQL
    from sqlalchemy.future import select
    from app.core.database import AsyncSessionLocal
    from app.domain.models.conversation import Conversation, ConversationStage
    from app.ai.routing import route_message
    from app.messaging.factory import get_whatsapp_provider

    async with AsyncSessionLocal() as db:
        stmt = select(Conversation).where(Conversation.customer_phone == phone)
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        
        if not conv:
            conv = Conversation(customer_phone=phone, stage=ConversationStage.negotiation)
            db.add(conv)
            await db.commit()
            await db.refresh(conv)
        else:
            conv.turn_count += 1
            await db.commit()

        stage_name = conv.stage.value if hasattr(conv.stage, 'value') else str(conv.stage)

    # ── Redis stage override (most reliable source of truth) ──────────────
    # registrar_decision_de_compra saves "stage": "closing" to Redis when transitioning.
    # If that key exists, it overrides the DB stage to ensure the closing agent
    # kicks in on the NEXT message, even if the DB commit had any issue.
    redis_state = await session_mgr.get_state(phone)
    redis_stage = redis_state.get("stage")
    if redis_stage and redis_stage != stage_name:
        logger.info(
            "webhook.stage.redis_override",
            phone=phone,
            db_stage=stage_name,
            redis_stage=redis_stage,
        )
        stage_name = redis_stage

    logger.info("webhook.stage.resolved", phone=phone, stage=stage_name)

    # 2. Call AI Router
    try:
        reply_text = await route_message(phone, text, stage_name)
    except Exception as e:
        logger.error("webhook.ai_routing.failed", error=str(e), phone=phone)
        reply_text = "Disculpá, el sistema está un poco saturado en este segundo. ¿Me repetís?"

    # 3. Send response via Evolution
    adapter = get_whatsapp_provider()
    try:
        await adapter.send_message(f"{phone}@s.whatsapp.net", reply_text)
    except Exception as e:
        logger.error("webhook.send_message.failed", error=str(e), phone=phone)



# ── Evolution API webhook ──────────────────────────────────────────────────────
@router.post("/evolution", status_code=http_status.HTTP_200_OK)
async def evolution_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
    apikey: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Receives Evolution API v2.3.7 webhook events.

    Evolution is configured with WEBHOOK_GLOBAL_URL pointing here.
    Responds 200 OK immediately; processing happens in background.
    """
    # Validate API key header
    expected_key = settings.evolution_api_key.get_secret_value()
    if apikey != expected_key:
        logger.warning("webhook.evolution.unauthorized")
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED)

    payload: dict[str, Any] = await request.json()
    background_tasks.add_task(_process_whatsapp_message, payload, redis)

    return {"status": "received"}


# ── Meta Cloud API webhook ─────────────────────────────────────────────────────
@router.get("/meta", status_code=http_status.HTTP_200_OK)
async def meta_webhook_verify(
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
) -> int | dict[str, str]:
    """
    Meta webhook verification challenge (GET).
    Meta sends this once when you configure the webhook URL.
    """
    expected = settings.meta_webhook_verify_token.get_secret_value()

    if hub_mode == "subscribe" and hub_verify_token == expected:
        logger.info("webhook.meta.verified")
        return int(hub_challenge or "0")

    raise HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail="Invalid verify token",
    )


@router.post("/meta", status_code=http_status.HTTP_200_OK)
async def meta_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    """
    Receives Meta Cloud API webhook events (POST).

    Meta requires a 200 OK within 20 seconds or it retries.
    We respond immediately and offload work to background.
    """
    # TODO: validate X-Hub-Signature-256 header for security (Phase 2)
    payload: dict[str, Any] = await request.json()
    background_tasks.add_task(_process_whatsapp_message, payload, redis)
    return {"status": "received"}


# ── Unified router (auto-dispatches based on active provider) ─────────────────
@router.post("", status_code=http_status.HTTP_200_OK)
async def unified_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    """
    Single unified endpoint: POST /webhooks/whatsapp

    Evolution is configured to POST here via WEBHOOK_GLOBAL_URL.
    The active provider is determined by settings.WHATSAPP_PROVIDER.
    """
    payload: dict[str, Any] = await request.json()
    background_tasks.add_task(_process_whatsapp_message, payload, redis)
    return {"status": "received"}
