"""
Notification infrastructure abstraction.

Supports in-app messaging alerts, ready for future email & push integrations.
"""

import logging
from typing import Optional

logger = logging.getLogger("ventureai.notifications")


def send_chat_notification(
    recipient_id: int,
    sender_name: str,
    message_preview: str,
    conversation_id: int,
):
    """
    Dispatch notification to user when a new chat message arrives.

    Future extension point for Email, In-app alerts, or WebPush notifications.
    """
    title = f"New message from {sender_name}"
    link = f"/chat.html?conversation_id={conversation_id}"
    logger.info(
        f"[NOTIFICATION] To User {recipient_id}: '{title}' - '{message_preview}' (link: {link})"
    )
    # Architecture is notification-ready: hook external push/email provider here if needed.
