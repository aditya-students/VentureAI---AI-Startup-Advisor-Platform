"""
REST API Router and WebSocket Endpoint for Mentor-Founder Chat.
"""

import json
from typing import Optional

from fastapi import (
    APIRouter, Depends, Query, File, UploadFile,
    WebSocket, WebSocketDisconnect, HTTPException, status
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User, MentorProfile
from app.auth.dependencies import get_current_user
from app.chat import service, storage
from app.chat.websocket import ws_manager, get_ws_authenticated_user
from app.chat.schemas import (
    ConversationCreate, ConversationResponse, ConversationListResponse,
    MessageCreate, MessageResponse, MessageListResponse
)
from app.chat.models import Conversation, MessageReadStatus

router = APIRouter(prefix="/mentor", tags=["Mentor Chat"])


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@router.post("/conversations", response_model=ConversationResponse, status_code=200)
def get_or_create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or return an existing active conversation for an active mentorship."""
    return service.get_or_create_conversation(
        db, current_user, connection_id=payload.connection_id, mentor_id=payload.mentor_id
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated list of conversations for current authenticated user."""
    return service.list_conversations(db, current_user, page=page, limit=limit)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detail for a specific conversation."""
    return service.get_conversation_detail(db, conversation_id, current_user)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None, description="Fetch messages older than this message ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated message thread history."""
    return service.get_conversation_messages(
        db, conversation_id, current_user, limit=limit, before_id=before_id
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send and persist a text message. Broadcasts real-time event via WebSockets."""
    msg_res = service.send_message(
        db, conversation_id, current_user, payload.content, message_type=payload.message_type
    )

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        recipient_id = service._get_recipient_user_id(db, conv, current_user.id)
        # Check if recipient is online & update delivery
        if ws_manager.is_user_online(recipient_id):
            read_rec = (
                db.query(MessageReadStatus)
                .filter(
                    MessageReadStatus.message_id == msg_res.id,
                    MessageReadStatus.user_id == recipient_id,
                )
                .first()
            )
            if read_rec and not read_rec.delivered_at:
                from datetime import datetime, timezone
                read_rec.delivered_at = datetime.now(timezone.utc)
                db.commit()
                msg_res.delivered_at = read_rec.delivered_at

        # Broadcast WebSocket event to both sender and recipient
        event = {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": msg_res.model_dump(mode="json"),
        }
        await ws_manager.broadcast_to_users(event, [current_user.id, recipient_id])

    return msg_res


@router.post("/conversations/{conversation_id}/attachments", response_model=MessageResponse, status_code=201)
async def upload_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file attachment and send it as a message."""
    att_data = storage.save_attachment_file(file)
    content = f"Attached file: {att_data[0]}"

    msg_res = service.send_message(
        db,
        conversation_id,
        current_user,
        content=content,
        message_type="file",
        attachment_data=att_data,
    )

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        recipient_id = service._get_recipient_user_id(db, conv, current_user.id)
        event = {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": msg_res.model_dump(mode="json"),
        }
        await ws_manager.broadcast_to_users(event, [current_user.id, recipient_id])

    return msg_res


@router.post("/messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single message as read."""
    success = service.mark_single_message_read(db, message_id, current_user)
    return {"success": success}


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread messages in conversation as read for current user."""
    count = service.mark_messages_read(db, conversation_id, current_user)

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        recipient_id = service._get_recipient_user_id(db, conv, current_user.id)
        event = {
            "type": "messages_read",
            "conversation_id": conversation_id,
            "reader_id": current_user.id,
        }
        await ws_manager.send_personal_message(event, recipient_id)

    return {"success": True, "read_count": count}


@router.post("/conversations/{conversation_id}/archive", response_model=ConversationResponse)
def archive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Archive a conversation."""
    return service.archive_conversation(db, conversation_id, current_user)


@router.get("/chat/attachments/{storage_reference}")
def get_attachment_file(
    storage_reference: str,
    current_user: User = Depends(get_current_user),
):
    """Securely download an attachment file."""
    path = storage.get_attachment_path(storage_reference)
    return FileResponse(path)


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@router.websocket("/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Real-time WebSocket endpoint for instant messaging and presence.
    """
    user = await get_ws_authenticated_user(websocket, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    is_part, _ = service._verify_conversation_participant(db, conv, user)
    if not is_part:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept & register connection
    await ws_manager.connect(websocket, user.id)

    # Automatically mark conversation messages as read when connecting to thread
    service.mark_messages_read(db, conversation_id, user)
    recipient_id = service._get_recipient_user_id(db, conv, user.id)

    # Notify recipient of reader status & online presence
    await ws_manager.send_personal_message(
        {
            "type": "presence_update",
            "user_id": user.id,
            "status": "online",
            "conversation_id": conversation_id,
        },
        recipient_id,
    )

    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
            except Exception:
                continue

            msg_type = data.get("type")

            if msg_type == "send_message":
                content = data.get("content", "")
                if content:
                    msg_res = service.send_message(
                        db, conversation_id, user, content
                    )
                    event = {
                        "type": "new_message",
                        "conversation_id": conversation_id,
                        "message": msg_res.model_dump(mode="json"),
                    }
                    await ws_manager.broadcast_to_users(event, [user.id, recipient_id])

            elif msg_type == "typing_start":
                await ws_manager.send_personal_message(
                    {
                        "type": "typing_start",
                        "conversation_id": conversation_id,
                        "user_id": user.id,
                        "user_name": user.name,
                    },
                    recipient_id,
                )

            elif msg_type == "typing_stop":
                await ws_manager.send_personal_message(
                    {
                        "type": "typing_stop",
                        "conversation_id": conversation_id,
                        "user_id": user.id,
                    },
                    recipient_id,
                )

            elif msg_type == "mark_read":
                service.mark_messages_read(db, conversation_id, user)
                await ws_manager.send_personal_message(
                    {
                        "type": "messages_read",
                        "conversation_id": conversation_id,
                        "reader_id": user.id,
                    },
                    recipient_id,
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user.id)
        # Notify recipient of offline status
        await ws_manager.send_personal_message(
            {
                "type": "presence_update",
                "user_id": user.id,
                "status": "offline",
                "conversation_id": conversation_id,
            },
            recipient_id,
        )
