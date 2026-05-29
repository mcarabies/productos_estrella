"""
Evolution API v2.3.7 — Concrete Adapter.
Implements WhatsAppProviderProtocol.

Key feature: asyncio.sleep() dynamic typing simulation before sending,
to make messages feel human and avoid WhatsApp spam detection.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.messaging.providers.evolution.schemas import (
    EvolutionMediaPayload,
    EvolutionTextPayload,
)

logger = get_logger(__name__)

# MIME types mapping for media
_MIME_MAP: dict[str, str] = {
    "image": "image/jpeg",
    "video": "video/mp4",
    "document": "application/pdf",
    "audio": "audio/ogg; codecs=opus",
}


class EvolutionAdapter:
    """
    Adapter for Evolution API v2.3.7 (self-hosted).

    All HTTP calls are async via httpx.AsyncClient.
    A shared client is created lazily to reuse connections.
    """

    def __init__(self) -> None:
        self._base_url = str(settings.evolution_api_url).rstrip("/")
        self._api_key = settings.evolution_api_key.get_secret_value()
        self._instance = settings.evolution_instance_name
        self._typing_min = settings.evolution_typing_min
        self._typing_max = settings.evolution_typing_max
        self._client: httpx.AsyncClient | None = None

    @property
    def _http(self) -> httpx.AsyncClient:
        """Lazy-initialize a persistent httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "apikey": self._api_key,
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    # ── Typing simulation ──────────────────────────────────────────────────────
    async def _simulate_typing(self, phone: str, text: str) -> None:
        """
        Wait a dynamic amount of time proportional to message length,
        then simulate the typing indicator (if the endpoint exists).

        The delay is randomized between evolution_typing_min and max to avoid
        fixed-interval detection by WhatsApp anti-spam systems.
        """
        # Scale delay with message length (longer message = longer "typing" time)
        char_factor = min(len(text) / 100, 1.0)  # clamp to [0, 1]
        delay = self._typing_min + (
            (self._typing_max - self._typing_min) * char_factor
        )
        # Add jitter ±20% to break patterns
        delay *= random.uniform(0.8, 1.2)

        logger.debug(
            "evolution.typing_delay",
            phone=phone,
            delay_seconds=round(delay, 2),
        )
        await asyncio.sleep(delay)

    # ── Internal HTTP helper ───────────────────────────────────────────────────
    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{endpoint}/{self._instance}"
        try:
            response = await self._http.post(url, json=payload)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as exc:
            logger.error(
                "evolution.http_error",
                status=exc.response.status_code,
                body=exc.response.text,
                url=url,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("evolution.request_error", error=str(exc), url=url)
            raise

    # ── WhatsAppProviderProtocol implementation ────────────────────────────────
    async def send_message(
        self,
        phone: str,
        text: str,
        *,
        quote_message_id: str | None = None,
    ) -> dict[str, Any]:
        await self._simulate_typing(phone, text)

        payload = EvolutionTextPayload(
            number=phone,
            text=text,
            quoted={"key": {"id": quote_message_id}} if quote_message_id else None,
        ).model_dump(exclude_none=True)

        result = await self._post("/message/sendText", payload)
        logger.info("evolution.send_message", phone=phone, chars=len(text))
        return result

    async def send_template(
        self,
        phone: str,
        template_name: str,
        language_code: str = "es",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Evolution doesn't natively support WhatsApp templates in the same way
        Meta does. This sends a regular text message instead.
        For production template support, upgrade to Meta provider.
        """
        logger.warning(
            "evolution.template_as_text",
            template=template_name,
            note="Evolution doesn't support official templates; sending as text",
        )
        return await self.send_message(phone, f"[{template_name}]")

    async def send_media(
        self,
        phone: str,
        media_url: str,
        media_type: str,
        caption: str | None = None,
    ) -> dict[str, Any]:
        await self._simulate_typing(phone, caption or "")

        payload = EvolutionMediaPayload(
            number=phone,
            mediatype=media_type,  # type: ignore[arg-type]
            mimetype=_MIME_MAP.get(media_type, "application/octet-stream"),
            caption=caption,
            media=media_url,
        ).model_dump(exclude_none=True)

        result = await self._post("/message/sendMedia", payload)
        logger.info("evolution.send_media", phone=phone, media_type=media_type)
        return result

    async def mark_as_read(self, message_id: str) -> dict[str, Any]:
        payload = {
            "readMessages": [{"id": message_id}],
        }
        return await self._post("/chat/markMessageAsRead", payload)

    async def send_typing(self, phone: str, duration_seconds: float) -> None:
        await asyncio.sleep(duration_seconds)
