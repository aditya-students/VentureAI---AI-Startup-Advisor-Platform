"""
Pydantic schemas for Mentor-Founder Chat API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AttachmentResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    storage_reference: str
    download_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReadStatusResponse(BaseModel):
    user_id: int
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserParticipantBrief(BaseModel):
    id: int
    name: str
    profile_image: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class MentorParticipantBrief(BaseModel):
    id: int
    user_id: int
    name: str
    profile_image: Optional[str] = None
    headline: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True


class StartupWorkspaceBrief(BaseModel):
    id: int
    name: str
    industry: Optional[str] = None
    stage: Optional[str] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    message_type: str = Field(default="text")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender: UserParticipantBrief
    message_type: str
    content: str
    created_at: datetime
    updated_at: datetime
    attachments: List[AttachmentResponse] = []
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    is_read: bool = False

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    has_more: bool
    next_before_id: Optional[int] = None


class ConversationCreate(BaseModel):
    connection_id: Optional[int] = None
    mentor_id: Optional[int] = None


class ConversationResponse(BaseModel):
    id: int
    connection_id: Optional[int] = None
    workspace_id: Optional[int] = None
    founder_id: int
    mentor_id: int
    status: str
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    founder: UserParticipantBrief
    mentor: MentorParticipantBrief
    workspace: Optional[StartupWorkspaceBrief] = None
    unread_count: int = 0
    last_message: Optional[MessageResponse] = None

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    limit: int
    total_pages: int
