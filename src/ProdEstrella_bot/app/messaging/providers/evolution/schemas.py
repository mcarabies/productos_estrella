"""
Evolution API v2.3.7 — Request/Response Schemas (Pydantic V2).
Only used internally by EvolutionAdapter; never exposed to business logic.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Outbound ───────────────────────────────────────────────────────────────────

class EvolutionTextPayload(BaseModel):
    """POST /message/sendText/{instance}"""
    number: str
    text: str
    quoted: dict[str, Any] | None = None
    delay: int = 0  # ms — simulated delay in Evolution itself


class EvolutionMediaPayload(BaseModel):
    """POST /message/sendMedia/{instance}"""
    number: str
    mediatype: Literal["image", "video", "document", "audio"]
    mimetype: str
    caption: str | None = None
    media: str  # URL or base64


class EvolutionTemplatePayload(BaseModel):
    """POST /message/sendTemplate/{instance} — stub, Evolution uses custom flows"""
    number: str
    name: str
    language: str = "es"
    components: list[dict[str, Any]] = Field(default_factory=list)


# ── Inbound Webhook ────────────────────────────────────────────────────────────

class EvolutionInboundMessage(BaseModel):
    """Normalized Evolution webhook payload for incoming messages."""
    event: str
    instance: str
    data: dict[str, Any]

    @property
    def sender_phone(self) -> str:
        """Extract sender number from JID (e.g. '5491112345678@s.whatsapp.net')."""
        jid: str = self.data.get("key", {}).get("remoteJid", "")
        return jid.split("@")[0]

    @property
    def message_text(self) -> str | None:
        """Extract plain text from message payload."""
        msg = self.data.get("message", {})
        return (
            msg.get("conversation")
            or (msg.get("extendedTextMessage") or {}).get("text")
        )

    @property
    def message_id(self) -> str:
        return self.data.get("key", {}).get("id", "")
