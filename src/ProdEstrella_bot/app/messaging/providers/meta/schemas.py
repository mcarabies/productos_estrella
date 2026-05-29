"""
Meta Cloud API — Request/Response Schemas (Pydantic V2).
Only used internally by MetaAdapter; never exposed to business logic.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Outbound helpers ────────────────────────────────────────────────────────────

class MetaTextBody(BaseModel):
    body: str


class MetaImageObject(BaseModel):
    link: str
    caption: str | None = None


class MetaDocumentObject(BaseModel):
    link: str
    caption: str | None = None
    filename: str = "document"


class MetaTemplateLanguage(BaseModel):
    code: str = "es"


class MetaTemplatePayload(BaseModel):
    name: str
    language: MetaTemplateLanguage = Field(default_factory=MetaTemplateLanguage)
    components: list[dict[str, Any]] = Field(default_factory=list)


class MetaOutboundMessage(BaseModel):
    """Base structure for Meta /messages API."""
    messaging_product: Literal["whatsapp"] = "whatsapp"
    recipient_type: Literal["individual"] = "individual"
    to: str  # E.164 phone number, no '+'


class MetaTextMessage(MetaOutboundMessage):
    type: Literal["text"] = "text"
    text: MetaTextBody
    context: dict[str, str] | None = None  # for quoting


class MetaMediaMessage(MetaOutboundMessage):
    type: Literal["image", "video", "document", "audio"]
    image: MetaImageObject | None = None
    document: MetaDocumentObject | None = None


class MetaTemplateMessage(MetaOutboundMessage):
    type: Literal["template"] = "template"
    template: MetaTemplatePayload


# ── Inbound Webhook ────────────────────────────────────────────────────────────

class MetaInboundEntry(BaseModel):
    """Normalized entry from Meta webhook payload."""
    id: str  # WhatsApp Business Account ID
    changes: list[dict[str, Any]]

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Extract all messages from changes."""
        result: list[dict[str, Any]] = []
        for change in self.changes:
            value = change.get("value", {})
            result.extend(value.get("messages", []))
        return result


class MetaWebhookPayload(BaseModel):
    """Top-level Meta webhook payload."""
    object: str
    entry: list[MetaInboundEntry]
