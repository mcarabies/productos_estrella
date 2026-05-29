"""
WhatsApp Provider Protocol — Clean Architecture interface.
Both Evolution and Meta adapters MUST implement this Protocol.
Business logic ONLY talks to this interface, never to concrete adapters.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WhatsAppProviderProtocol(Protocol):
    """
    Abstract contract for any WhatsApp messaging provider.

    All methods are async and must not block the event loop.
    """

    async def send_message(
        self,
        phone: str,
        text: str,
        *,
        quote_message_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a plain text message to *phone*.

        Args:
            phone: Recipient in E.164 format (e.g. '5491112345678').
            text: Message body.
            quote_message_id: Optional ID of a message to quote/reply to.

        Returns:
            Provider-specific response dict (normalized upstream).
        """
        ...

    async def send_template(
        self,
        phone: str,
        template_name: str,
        language_code: str = "es",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Send a pre-approved WhatsApp template message.

        Args:
            phone: Recipient in E.164 format.
            template_name: Template name as registered in WA Business Manager.
            language_code: BCP 47 language code (default: 'es').
            components: Variable substitution components.

        Returns:
            Provider-specific response dict.
        """
        ...

    async def send_media(
        self,
        phone: str,
        media_url: str,
        media_type: str,
        caption: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a media message (image, document, video, audio).

        Args:
            phone: Recipient in E.164 format.
            media_url: Publicly accessible URL of the media file.
            media_type: MIME category: 'image' | 'document' | 'video' | 'audio'.
            caption: Optional caption for image/video/document.

        Returns:
            Provider-specific response dict.
        """
        ...

    async def mark_as_read(self, message_id: str) -> dict[str, Any]:
        """
        Send a read receipt for *message_id*.

        Args:
            message_id: Provider-specific message identifier.

        Returns:
            Provider-specific response dict.
        """
        ...

    async def send_typing(self, phone: str, duration_seconds: float) -> None:
        """
        Simulate typing indicator for *duration_seconds*.

        Args:
            phone: Recipient in E.164 format.
            duration_seconds: How long to show typing (then send).
        """
        ...
