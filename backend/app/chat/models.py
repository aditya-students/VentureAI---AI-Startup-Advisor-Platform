"""
Database models for Mentor-Founder Chat/Communication System.

Tables:
- conversations
- messages
- message_attachments
- message_read_status
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum,
    Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    READ_ONLY = "read_only"


class MessageType(str, enum.Enum):
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"


class Conversation(Base):
    """
    Relationship-aware conversation entity between a Founder and a Mentor
    for a specific Workspace/Startup.
    """
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("founder_id", "mentor_id", "workspace_id", name="uq_conversations_founder_mentor_workspace"),
        Index("ix_conversations_founder_id", "founder_id"),
        Index("ix_conversations_mentor_id", "mentor_id"),
        Index("ix_conversations_workspace_id", "workspace_id"),
        Index("ix_conversations_connection_id", "connection_id"),
        Index("ix_conversations_last_message_at", "last_message_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(
        Integer,
        ForeignKey("mentorships.id", ondelete="SET NULL"),
        nullable=True,
    )
    founder_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mentor_id = Column(
        Integer,
        ForeignKey("mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        Integer,
        ForeignKey("startups.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        Enum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.ACTIVE,
        nullable=False,
    )
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    founder = relationship("User", foreign_keys=[founder_id])
    mentor_profile = relationship("MentorProfile", foreign_keys=[mentor_id])
    workspace = relationship("Startup", foreign_keys=[workspace_id])
    connection = relationship("Mentorship", foreign_keys=[connection_id])
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )


class Message(Base):
    """
    A persistent chat message within a conversation.
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_sender_id", "sender_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_type = Column(
        Enum(MessageType, name="message_type"),
        default=MessageType.TEXT,
        nullable=False,
    )
    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    attachments = relationship(
        "MessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
    )
    read_statuses = relationship(
        "MessageReadStatus",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class MessageAttachment(Base):
    """
    File attachment linked to a message.
    """
    __tablename__ = "message_attachments"
    __table_args__ = (
        Index("ix_message_attachments_message_id", "message_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_reference = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Relationships ---
    message = relationship("Message", back_populates="attachments")


class MessageReadStatus(Base):
    """
    Delivery & Read receipt status for a message per recipient user.
    """
    __tablename__ = "message_read_status"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_read_status_message_user"),
        Index("ix_message_read_status_user_read", "user_id", "read_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # --- Relationships ---
    message = relationship("Message", back_populates="read_statuses")
    user = relationship("User", foreign_keys=[user_id])
