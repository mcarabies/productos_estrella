"""
Meta Cloud API — Concrete Adapter.
Implements WhatsAppProviderProtocol using the official Meta Graph API.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.messaging.providers.meta.schemas import (
    MetaMediaMessage,
    MetaTemplateMessage,
    MetaTemplatePayload,
    MetaTextBody,
    MetaTextMessage,
)

logger = get_logger(__name__)

_GRAPH_API_VERSION = "v22.0"
_GRAPH_API_BASE = f"https://graph.facebook.com/{_GRAPH_API_VERSION}"


class MetaAdapter:
    """
    Adapter for Meta Cloud API (official WhatsApp Business Platform).

    Uses httpx.AsyncClient for fully non-blocking HTTP calls.
    """

    def __init__(self) -> None:
        self._phone_number_id = settings.meta_phone_number_id
        self._token = settings.meta_whatsapp_token.get_secret_value()
        self._client: httpx.AsyncClient | None = None

    @property
    def _http(self) -> httpx.AsyncClient:
        """Lazy-initialize a persistent httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=_GRAPH_API_BASE,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    @property
    def _messages_url(self) -> str:
        return f"/{self._phone_number_id}/messages"

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http.post(self._messages_url, json=payload)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as exc:
            logger.error(
                "meta.http_error",
                status=exc.response.status_code,
                body=exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("meta.request_error", error=str(exc))
            raise

    # ── WhatsAppProviderProtocol implementation ────────────────────────────────
    async def send_message(
        self,
        phone: str,
        text: str,
        *,
        quote_message_id: str | None = None,
    ) -> dict[str, Any]:
        msg = MetaTextMessage(
            to=phone,
            text=MetaTextBody(body=text),
            context={"message_id": quote_message_id} if quote_message_id else None,
        )
        result = await self._post(msg.model_dump(exclude_none=True))
        logger.info("meta.send_message", phone=phone, chars=len(text))
        return result

    async def send_template(
        self,
        phone: str,
        template_name: str,
        language_code: str = "es",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        msg = MetaTemplateMessage(
            to=phone,
            template=MetaTemplatePayload(
                name=template_name,
                language={"code": language_code},  # type: ignore[arg-type]
                components=components or [],
            ),
        )
        result = await self._post(msg.model_dump(exclude_none=True))
        logger.info("meta.send_template", phone=phone, template=template_name)
        return result

    async def send_media(
        self,
        phone: str,
        media_url: str,
        media_type: str,
        caption: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": media_type,
            media_type: {"link": media_url, "caption": caption},
        }
        result = await self._post(payload)
        logger.info("meta.send_media", phone=phone, media_type=media_type)
        return result

    async def mark_as_read(self, message_id: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._post(payload)

    async def send_typing(self, phone: str, duration_seconds: float) -> None:
        """Meta Cloud API doesn't support explicit typing indicators via API."""
        import asyncio
        await asyncio.sleep(duration_seconds)
        logger.debug("meta.send_typing_noop", phone=phone)
