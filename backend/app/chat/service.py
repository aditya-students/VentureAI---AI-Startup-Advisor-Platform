"""
Mentor-Founder Chat Business Logic & Data Access Service.
"""

import html
import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from app.users.models import User, MentorProfile, RoleName
from app.startup.models import Startup
from app.mentorship.models import Mentorship, MentorshipRequest, MentorshipStatus, RequestStatus
from app.chat.models import Conversation, Message, MessageAttachment, MessageReadStatus, ConversationStatus, MessageType
from app.chat.schemas import (
    ConversationResponse, ConversationListResponse,
    MessageResponse, MessageListResponse, AttachmentResponse,
    UserParticipantBrief, MentorParticipantBrief, StartupWorkspaceBrief
)
from app.notifications.service import send_chat_notification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_message_content(content: str) -> str:
    """Trim whitespace and escape HTML to prevent script injection while preserving formatting."""
    cleaned = content.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or only whitespace.",
        )
    if len(cleaned) > 4000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message exceeds maximum length of 4000 characters.",
        )
    return html.escape(cleaned)


def _get_user_mentor_profile(db: Session, user_id: int) -> Optional[MentorProfile]:
    return db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()


def _verify_conversation_participant(
    db: Session,
    conversation: Conversation,
    current_user: User,
) -> Tuple[bool, str]:
    """
    Returns (is_participant, role_in_conversation).
    role_in_conversation is 'founder' or 'mentor'.
    """
    if conversation.founder_id == current_user.id:
        return True, "founder"

    mentor_profile = _get_user_mentor_profile(db, current_user.id)
    if mentor_profile and conversation.mentor_id == mentor_profile.id:
        return True, "mentor"

    return False, ""


def _get_recipient_user_id(db: Session, conversation: Conversation, sender_user_id: int) -> int:
    """Determine recipient user ID based on conversation participants."""
    if sender_user_id == conversation.founder_id:
        # Recipient is mentor's user ID
        mentor_profile = db.query(MentorProfile).filter(MentorProfile.id == conversation.mentor_id).first()
        return mentor_profile.user_id if mentor_profile else 0
    else:
        # Recipient is founder
        return conversation.founder_id


def _build_user_brief(user: User) -> UserParticipantBrief:
    return UserParticipantBrief(
        id=user.id,
        name=user.name,
        profile_image=user.profile_image,
        role=user.role.name if user.role else "Founder",
    )


def _build_mentor_brief(db: Session, mentor_profile_id: int) -> MentorParticipantBrief:
    profile = db.query(MentorProfile).filter(MentorProfile.id == mentor_profile_id).first()
    mentor_user = db.query(User).filter(User.id == profile.user_id).first() if profile else None
    return MentorParticipantBrief(
        id=profile.id if profile else 0,
        user_id=profile.user_id if profile else 0,
        name=mentor_user.name if mentor_user else "Mentor",
        profile_image=mentor_user.profile_image if mentor_user else None,
        headline=profile.headline if profile else None,
        company=profile.company if profile else None,
    )


def _build_startup_brief(startup: Optional[Startup]) -> Optional[StartupWorkspaceBrief]:
    if not startup:
        return None
    return StartupWorkspaceBrief(
        id=startup.id,
        name=startup.name,
        industry=startup.industry,
        stage=startup.stage.value if hasattr(startup.stage, 'value') else str(startup.stage) if startup.stage else "Idea",
    )


def _build_attachment_response(att: MessageAttachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=att.id,
        file_name=att.file_name,
        file_type=att.file_type,
        file_size=att.file_size,
        storage_reference=att.storage_reference,
        download_url=f"/mentor/chat/attachments/{att.storage_reference}",
        created_at=att.created_at,
    )


def _build_message_response(db: Session, message: Message, current_user_id: int) -> MessageResponse:
    sender_user = db.query(User).filter(User.id == message.sender_id).first()
    read_status = (
        db.query(MessageReadStatus)
        .filter(MessageReadStatus.message_id == message.id)
        .first()
    )

    attachments = [
        _build_attachment_response(att) for att in message.attachments
    ]

    is_read = False
    if read_status:
        is_read = read_status.read_at is not None

    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender=_build_user_brief(sender_user),
        message_type=message.message_type.value if hasattr(message.message_type, 'value') else str(message.message_type),
        content=message.content,
        created_at=message.created_at,
        updated_at=message.updated_at,
        attachments=attachments,
        delivered_at=read_status.delivered_at if read_status else None,
        read_at=read_status.read_at if read_status else None,
        is_read=is_read,
    )


# ---------------------------------------------------------------------------
# Conversation Operations
# ---------------------------------------------------------------------------

def get_or_create_conversation(
    db: Session,
    current_user: User,
    connection_id: Optional[int] = None,
    mentor_id: Optional[int] = None,
) -> ConversationResponse:
    """
    Get existing active conversation or create one if a valid ACTIVE mentorship exists.

    Enforces relationship check:
    - Must have status = ACTIVE in mentorships table.
    """
    mentorship: Optional[Mentorship] = None

    if connection_id:
        mentorship = db.query(Mentorship).filter(Mentorship.id == connection_id).first()
    elif mentor_id:
        if current_user.role.name == "Founder":
            mentorship = (
                db.query(Mentorship)
                .filter(
                    Mentorship.founder_id == current_user.id,
                    Mentorship.mentor_id == mentor_id,
                    Mentorship.status == MentorshipStatus.ACTIVE,
                )
                .first()
            )
        elif current_user.role.name == "Mentor":
            mentor_profile = _get_user_mentor_profile(db, current_user.id)
            if mentor_profile:
                mentorship = (
                    db.query(Mentorship)
                    .filter(
                        Mentorship.mentor_id == mentor_profile.id,
                        Mentorship.status == MentorshipStatus.ACTIVE,
                    )
                    .first()
                )

    if not mentorship:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat is unavailable. A valid and active mentorship connection is required.",
        )

    if mentorship.status != MentorshipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot initiate active chat. Mentorship status is '{mentorship.status.value}'.",
        )

    # Check ownership of mentorship
    is_founder = mentorship.founder_id == current_user.id
    mentor_profile = db.query(MentorProfile).filter(MentorProfile.id == mentorship.mentor_id).first()
    is_mentor = mentor_profile and mentor_profile.user_id == current_user.id

    if not (is_founder or is_mentor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this mentorship conversation.",
        )

    # Lookup existing conversation
    existing_conv = (
        db.query(Conversation)
        .filter(
            Conversation.founder_id == mentorship.founder_id,
            Conversation.mentor_id == mentorship.mentor_id,
            Conversation.workspace_id == mentorship.workspace_id,
        )
        .first()
    )

    if existing_conv:
        # If conversation exists, return it
        return get_conversation_detail(db, existing_conv.id, current_user)

    # Create new active conversation
    conv = Conversation(
        connection_id=mentorship.id,
        founder_id=mentorship.founder_id,
        mentor_id=mentorship.mentor_id,
        workspace_id=mentorship.workspace_id,
        status=ConversationStatus.ACTIVE,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # Add initial system message
    system_msg = Message(
        conversation_id=conv.id,
        sender_id=current_user.id,
        message_type=MessageType.SYSTEM,
        content="Mentorship connection established. You can now chat.",
    )
    db.add(system_msg)
    conv.last_message_at = func.now()
    db.commit()

    return get_conversation_detail(db, conv.id, current_user)


def get_conversation_detail(
    db: Session,
    conversation_id: int,
    current_user: User,
) -> ConversationResponse:
    """Load single conversation detail with authorization check."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    is_part, _ = _verify_conversation_participant(db, conv, current_user)
    if not is_part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this conversation.",
        )

    # Sync status with underlying mentorship if ended
    if conv.connection:
        if conv.connection.status in (MentorshipStatus.COMPLETED, MentorshipStatus.CANCELLED):
            if conv.status != ConversationStatus.READ_ONLY:
                conv.status = ConversationStatus.READ_ONLY
                db.commit()

    founder_user = db.query(User).filter(User.id == conv.founder_id).first()
    mentor_profile = db.query(MentorProfile).filter(MentorProfile.id == conv.mentor_id).first()
    workspace = db.query(Startup).filter(Startup.id == conv.workspace_id).first() if conv.workspace_id else None

    # Calculate unread count for current user
    unread_count = (
        db.query(MessageReadStatus)
        .join(Message, MessageReadStatus.message_id == Message.id)
        .filter(
            Message.conversation_id == conv.id,
            MessageReadStatus.user_id == current_user.id,
            MessageReadStatus.read_at.is_(None),
        )
        .count()
    )

    # Last message
    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .first()
    )

    return ConversationResponse(
        id=conv.id,
        connection_id=conv.connection_id,
        workspace_id=conv.workspace_id,
        founder_id=conv.founder_id,
        mentor_id=conv.mentor_id,
        status=conv.status.value if hasattr(conv.status, 'value') else str(conv.status),
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        founder=_build_user_brief(founder_user),
        mentor=_build_mentor_brief(db, conv.mentor_id),
        workspace=_build_startup_brief(workspace),
        unread_count=unread_count,
        last_message=_build_message_response(db, last_msg, current_user.id) if last_msg else None,
    )


def list_conversations(
    db: Session,
    current_user: User,
    page: int = 1,
    limit: int = 20,
) -> ConversationListResponse:
    """Return paginated list of conversations for current authenticated user."""
    mentor_profile = _get_user_mentor_profile(db, current_user.id)
    mentor_profile_id = mentor_profile.id if mentor_profile else -1

    query = (
        db.query(Conversation)
        .filter(
            or_(
                Conversation.founder_id == current_user.id,
                Conversation.mentor_id == mentor_profile_id,
            )
        )
        .order_by(Conversation.last_message_at.desc().nullslast())
    )

    total = query.count()
    offset = (page - 1) * limit
    convs = query.offset(offset).limit(limit).all()
    total_pages = math.ceil(total / limit) if limit > 0 else 0

    items = [get_conversation_detail(db, c.id, current_user) for c in convs]

    return ConversationListResponse(
        conversations=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# Message Operations
# ---------------------------------------------------------------------------

def get_conversation_messages(
    db: Session,
    conversation_id: int,
    current_user: User,
    limit: int = 50,
    before_id: Optional[int] = None,
) -> MessageListResponse:
    """Fetch paginated message thread history."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    is_part, _ = _verify_conversation_participant(db, conv, current_user)
    if not is_part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view messages in this conversation.",
        )

    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    if before_id:
        query = query.filter(Message.id < before_id)

    query = query.order_by(Message.id.desc()).limit(limit + 1)
    results = query.all()

    has_more = len(results) > limit
    messages_slice = results[:limit]
    messages_slice.reverse()  # Chronological order

    next_before_id = messages_slice[0].id if (has_more and messages_slice) else None

    msg_responses = [_build_message_response(db, m, current_user.id) for m in messages_slice]

    return MessageListResponse(
        messages=msg_responses,
        has_more=has_more,
        next_before_id=next_before_id,
    )


def send_message(
    db: Session,
    conversation_id: int,
    current_user: User,
    content: str,
    message_type: str = "text",
    attachment_data: Optional[Tuple[str, str, int, str]] = None,
) -> MessageResponse:
    """
    Send and persist a new message in a conversation.
    Sender ID is derived directly from authenticated current_user.
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    is_part, _ = _verify_conversation_participant(db, conv, current_user)
    if not is_part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to send messages in this conversation.",
        )

    if conv.status in (ConversationStatus.READ_ONLY, ConversationStatus.ARCHIVED):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This mentorship has ended. Messaging is no longer available.",
        )

    sanitized_content = _sanitize_message_content(content)

    msg_type_enum = MessageType.TEXT
    if message_type == "file":
        msg_type_enum = MessageType.FILE
    elif message_type == "system":
        msg_type_enum = MessageType.SYSTEM

    msg = Message(
        conversation_id=conv.id,
        sender_id=current_user.id,
        message_type=msg_type_enum,
        content=sanitized_content,
    )
    db.add(msg)
    db.flush()

    # Attachment record
    if attachment_data:
        file_name, file_type, file_size, storage_ref = attachment_data
        attachment = MessageAttachment(
            message_id=msg.id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            storage_reference=storage_ref,
        )
        db.add(attachment)

    # Recipient read status entry
    recipient_user_id = _get_recipient_user_id(db, conv, current_user.id)
    read_status = MessageReadStatus(
        message_id=msg.id,
        user_id=recipient_user_id,
        delivered_at=None,
        read_at=None,
    )
    db.add(read_status)

    conv.last_message_at = func.now()
    db.commit()
    db.refresh(msg)

    # Dispatch notification alert
    send_chat_notification(
        recipient_id=recipient_user_id,
        sender_name=current_user.name,
        message_preview=sanitized_content[:60],
        conversation_id=conv.id,
    )

    return _build_message_response(db, msg, current_user.id)


def mark_messages_read(
    db: Session,
    conversation_id: int,
    current_user: User,
) -> int:
    """Mark all unread messages addressed to current_user in this conversation as read."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    is_part, _ = _verify_conversation_participant(db, conv, current_user)
    if not is_part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized conversation access.",
        )

    now = datetime.now(timezone.utc)
    unread_records = (
        db.query(MessageReadStatus)
        .join(Message, MessageReadStatus.message_id == Message.id)
        .filter(
            Message.conversation_id == conversation_id,
            MessageReadStatus.user_id == current_user.id,
            MessageReadStatus.read_at.is_(None),
        )
        .all()
    )

    count = len(unread_records)
    for rec in unread_records:
        rec.read_at = now
        if not rec.delivered_at:
            rec.delivered_at = now

    db.commit()
    return count


def mark_single_message_read(
    db: Session,
    message_id: int,
    current_user: User,
) -> bool:
    """Mark a single message as read by current user."""
    rec = (
        db.query(MessageReadStatus)
        .filter(
            MessageReadStatus.message_id == message_id,
            MessageReadStatus.user_id == current_user.id,
        )
        .first()
    )
    if rec:
        now = datetime.now(timezone.utc)
        rec.read_at = now
        if not rec.delivered_at:
            rec.delivered_at = now
        db.commit()
        return True
    return False


def archive_conversation(
    db: Session,
    conversation_id: int,
    current_user: User,
) -> ConversationResponse:
    """Archive a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    is_part, _ = _verify_conversation_participant(db, conv, current_user)
    if not is_part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized conversation access.",
        )

    conv.status = ConversationStatus.ARCHIVED
    db.commit()
    return get_conversation_detail(db, conv.id, current_user)
