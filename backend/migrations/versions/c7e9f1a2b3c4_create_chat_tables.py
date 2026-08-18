"""create_chat_tables

Revision ID: c7e9f1a2b3c4
Revises: b5d9e3f4a81c
Create Date: 2026-08-18 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e9f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'b5d9e3f4a81c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Table: conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), sa.ForeignKey('mentorships.id', ondelete='SET NULL'), nullable=True),
        sa.Column('founder_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mentor_id', sa.Integer(), sa.ForeignKey('mentor_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('startups.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('active', 'archived', 'read_only', name='conversation_status'), nullable=False, server_default='active'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('founder_id', 'mentor_id', 'workspace_id', name='uq_conversations_founder_mentor_workspace')
    )
    op.create_index('ix_conversations_id', 'conversations', ['id'])
    op.create_index('ix_conversations_founder_id', 'conversations', ['founder_id'])
    op.create_index('ix_conversations_mentor_id', 'conversations', ['mentor_id'])
    op.create_index('ix_conversations_workspace_id', 'conversations', ['workspace_id'])
    op.create_index('ix_conversations_connection_id', 'conversations', ['connection_id'])
    op.create_index('ix_conversations_last_message_at', 'conversations', ['last_message_at'])

    # 2. Table: messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_type', sa.Enum('text', 'file', 'system', name='message_type'), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_id', 'messages', ['id'])
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', 'created_at'])
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # 3. Table: message_attachments
    op.create_table(
        'message_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('storage_reference', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_message_attachments_id', 'message_attachments', ['id'])
    op.create_index('ix_message_attachments_message_id', 'message_attachments', ['message_id'])

    # 4. Table: message_read_status
    op.create_table(
        'message_read_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', name='uq_message_read_status_message_user')
    )
    op.create_index('ix_message_read_status_id', 'message_read_status', ['id'])
    op.create_index('ix_message_read_status_user_read', 'message_read_status', ['user_id', 'read_at'])


def downgrade() -> None:
    op.drop_table('message_read_status')
    op.drop_table('message_attachments')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.execute('DROP TYPE IF EXISTS message_type')
    op.execute('DROP TYPE IF EXISTS conversation_status')
