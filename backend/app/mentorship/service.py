"""
Mentorship Request business logic — kept separate from the router so route
handlers stay thin and this logic is independently testable.
"""

import math
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from fastapi import HTTPException, status

from app.users.models import User, MentorProfile, UserStatus
from app.startup.models import Startup
from app.mentorship.models import (
    MentorshipRequest, Mentorship,
    RequestStatus, MentorshipStatus,
)
from app.mentorship.schemas import (
    MentorshipRequestCreate,
    MentorshipRequestResponse,
    MentorshipRequestFounderCard,
    MentorshipRequestMentorCard,
    MentorshipCheckResponse,
    MentorBrief, FounderBrief, StartupBrief,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mentor_brief(profile: MentorProfile, user: User) -> MentorBrief:
    return MentorBrief(
        id=profile.id,
        name=user.name,
        profile_image=user.profile_image,
        headline=profile.headline,
        company=profile.company,
        availability=profile.availability,
    )


def _build_founder_brief(user: User) -> FounderBrief:
    return FounderBrief(
        id=user.id,
        name=user.name,
        profile_image=user.profile_image,
    )


def _build_startup_brief(startup: Optional[Startup]) -> Optional[StartupBrief]:
    if not startup:
        return None
    return StartupBrief(
        id=startup.id,
        name=startup.name,
        industry=startup.industry,
        stage=startup.stage.value if startup.stage else "Idea",
    )


def _build_full_response(
    req: MentorshipRequest,
    mentor_user: User,
    founder_user: User,
) -> MentorshipRequestResponse:
    return MentorshipRequestResponse(
        id=req.id,
        founder=_build_founder_brief(founder_user),
        mentor=_build_mentor_brief(req.mentor_profile, mentor_user),
        startup=_build_startup_brief(req.workspace),
        mentorship_area=req.mentorship_area,
        startup_stage=req.startup_stage,
        challenge=req.challenge,
        message=req.message,
        status=req.status.value,
        rejection_reason=req.rejection_reason,
        created_at=req.created_at,
        updated_at=req.updated_at,
        responded_at=req.responded_at,
    )


# ---------------------------------------------------------------------------
# Create request (Founder)
# ---------------------------------------------------------------------------

def create_request(
    db: Session,
    founder_id: int,
    data: MentorshipRequestCreate,
) -> MentorshipRequestResponse:
    """
    Create a mentorship request from a founder to a mentor.

    Validations:
    - Mentor profile exists and is discoverable
    - Mentor's user is active
    - Founder is not requesting themselves
    - No existing PENDING request for this founder→mentor pair
    - No existing ACTIVE mentorship for this pair
    """
    # Load mentor profile
    profile = (
        db.query(MentorProfile)
        .filter(MentorProfile.id == data.mentor_id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor not found.",
        )
    if not profile.is_discoverable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This mentor is currently unavailable for new mentorship requests.",
        )

    # Load mentor's user
    mentor_user = db.query(User).filter(User.id == profile.user_id).first()
    if not mentor_user or mentor_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This mentor is currently unavailable.",
        )

    # Prevent self-request
    if founder_id == profile.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot send a mentorship request to yourself.",
        )

    # Check for existing pending request
    existing_pending = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.founder_id == founder_id,
            MentorshipRequest.mentor_id == data.mentor_id,
            MentorshipRequest.status == RequestStatus.PENDING,
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending mentorship request with this mentor.",
        )

    # Check for existing active mentorship
    existing_mentorship = (
        db.query(Mentorship)
        .filter(
            Mentorship.founder_id == founder_id,
            Mentorship.mentor_id == data.mentor_id,
            Mentorship.status == MentorshipStatus.ACTIVE,
        )
        .first()
    )
    if existing_mentorship:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active mentorship with this mentor.",
        )

    # Auto-attach founder's startup
    startup = (
        db.query(Startup)
        .filter(Startup.founder_id == founder_id)
        .first()
    )

    # Create request
    req = MentorshipRequest(
        founder_id=founder_id,
        mentor_id=data.mentor_id,
        workspace_id=startup.id if startup else None,
        mentorship_area=data.mentorship_area,
        startup_stage=data.startup_stage,
        challenge=data.challenge,
        message=data.message,
        status=RequestStatus.PENDING,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Load founder user for response
    founder_user = db.query(User).filter(User.id == founder_id).first()

    return _build_full_response(req, mentor_user, founder_user)


# ---------------------------------------------------------------------------
# Founder: list sent requests
# ---------------------------------------------------------------------------

def get_founder_requests(
    db: Session,
    founder_id: int,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """Return paginated list of requests sent by this founder, newest first."""
    query = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.founder_id == founder_id)
        .order_by(MentorshipRequest.created_at.desc())
    )

    total = query.count()
    offset = (page - 1) * limit
    results = query.offset(offset).limit(limit).all()
    total_pages = math.ceil(total / limit) if limit > 0 else 0

    cards = []
    for req in results:
        profile = req.mentor_profile
        mentor_user = db.query(User).filter(User.id == profile.user_id).first()
        cards.append(MentorshipRequestFounderCard(
            id=req.id,
            mentor=_build_mentor_brief(profile, mentor_user),
            mentorship_area=req.mentorship_area,
            startup_stage=req.startup_stage,
            status=req.status.value,
            created_at=req.created_at,
            responded_at=req.responded_at,
        ))

    return {
        "requests": cards,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Mentor: list received requests
# ---------------------------------------------------------------------------

def get_mentor_requests(
    db: Session,
    mentor_profile_id: int,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None,
) -> dict:
    """Return paginated list of requests addressed to this mentor, newest first."""
    query = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.mentor_id == mentor_profile_id)
        .order_by(MentorshipRequest.created_at.desc())
    )

    if status_filter:
        try:
            rs = RequestStatus(status_filter)
            query = query.filter(MentorshipRequest.status == rs)
        except ValueError:
            pass  # Ignore invalid filter

    total = query.count()
    offset = (page - 1) * limit
    results = query.offset(offset).limit(limit).all()
    total_pages = math.ceil(total / limit) if limit > 0 else 0

    cards = []
    for req in results:
        founder_user = db.query(User).filter(User.id == req.founder_id).first()
        cards.append(MentorshipRequestMentorCard(
            id=req.id,
            founder=_build_founder_brief(founder_user),
            startup=_build_startup_brief(req.workspace),
            mentorship_area=req.mentorship_area,
            startup_stage=req.startup_stage,
            status=req.status.value,
            created_at=req.created_at,
        ))

    return {
        "requests": cards,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Request detail (both roles, ownership-verified)
# ---------------------------------------------------------------------------

def get_request_detail(
    db: Session,
    request_id: int,
    current_user: User,
) -> MentorshipRequestResponse:
    """
    Load a single request with full context.
    Founders can only see their own requests.
    Mentors can only see requests addressed to them.
    """
    req = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship request not found.",
        )

    # Ownership check
    user_role = current_user.role.name
    if user_role == "Founder" and req.founder_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this request.",
        )
    if user_role == "Mentor":
        mentor_profile = (
            db.query(MentorProfile)
            .filter(MentorProfile.user_id == current_user.id)
            .first()
        )
        if not mentor_profile or req.mentor_id != mentor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this request.",
            )

    # Build response
    mentor_user = db.query(User).filter(User.id == req.mentor_profile.user_id).first()
    founder_user = db.query(User).filter(User.id == req.founder_id).first()

    return _build_full_response(req, mentor_user, founder_user)


# ---------------------------------------------------------------------------
# Cancel request (Founder)
# ---------------------------------------------------------------------------

def cancel_request(
    db: Session,
    request_id: int,
    founder_id: int,
) -> MentorshipRequestResponse:
    """Cancel a pending request. Only the founder who created it can cancel."""
    req = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship request not found.",
        )
    if req.founder_id != founder_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this request.",
        )
    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel a request with status '{req.status.value}'. Only pending requests can be cancelled.",
        )

    req.status = RequestStatus.CANCELLED
    req.responded_at = func.now()
    db.commit()
    db.refresh(req)

    mentor_user = db.query(User).filter(User.id == req.mentor_profile.user_id).first()
    founder_user = db.query(User).filter(User.id == founder_id).first()

    return _build_full_response(req, mentor_user, founder_user)


# ---------------------------------------------------------------------------
# Accept request (Mentor)
# ---------------------------------------------------------------------------

def accept_request(
    db: Session,
    request_id: int,
    mentor_user_id: int,
) -> MentorshipRequestResponse:
    """
    Accept a pending request. Only the addressed mentor can accept.
    Creates a Mentorship row upon acceptance.
    """
    req = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship request not found.",
        )

    # Verify the authenticated mentor owns the addressed profile
    mentor_profile = (
        db.query(MentorProfile)
        .filter(MentorProfile.user_id == mentor_user_id)
        .first()
    )
    if not mentor_profile or req.mentor_id != mentor_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to accept this request.",
        )

    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot accept a request with status '{req.status.value}'. Only pending requests can be accepted.",
        )

    # Check for duplicate active mentorship
    existing = (
        db.query(Mentorship)
        .filter(
            Mentorship.founder_id == req.founder_id,
            Mentorship.mentor_id == req.mentor_id,
            Mentorship.status == MentorshipStatus.ACTIVE,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active mentorship already exists with this founder.",
        )

    # Update request status
    req.status = RequestStatus.ACCEPTED
    req.responded_at = func.now()

    # Create mentorship relationship
    mentorship = Mentorship(
        founder_id=req.founder_id,
        mentor_id=req.mentor_id,
        request_id=req.id,
        workspace_id=req.workspace_id,
        status=MentorshipStatus.ACTIVE,
    )
    db.add(mentorship)
    db.commit()
    db.refresh(mentorship)
    db.refresh(req)

    # Initialize chat conversation
    try:
        from app.chat.models import Conversation, ConversationStatus, Message, MessageType
        conv = Conversation(
            connection_id=mentorship.id,
            founder_id=req.founder_id,
            mentor_id=req.mentor_id,
            workspace_id=req.workspace_id,
            status=ConversationStatus.ACTIVE,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        sys_msg = Message(
            conversation_id=conv.id,
            sender_id=mentor_user_id,
            message_type=MessageType.SYSTEM,
            content="Mentorship request accepted. Mentorship connection established.",
        )
        db.add(sys_msg)
        conv.last_message_at = func.now()
        db.commit()
    except Exception:
        pass  # If conversation exists or creation fails, request accept succeeds regardless

    mentor_user = db.query(User).filter(User.id == mentor_user_id).first()
    founder_user = db.query(User).filter(User.id == req.founder_id).first()

    return _build_full_response(req, mentor_user, founder_user)


# ---------------------------------------------------------------------------
# Reject request (Mentor)
# ---------------------------------------------------------------------------

def reject_request(
    db: Session,
    request_id: int,
    mentor_user_id: int,
    rejection_reason: Optional[str] = None,
) -> MentorshipRequestResponse:
    """Reject a pending request. Only the addressed mentor can reject."""
    req = (
        db.query(MentorshipRequest)
        .filter(MentorshipRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship request not found.",
        )

    mentor_profile = (
        db.query(MentorProfile)
        .filter(MentorProfile.user_id == mentor_user_id)
        .first()
    )
    if not mentor_profile or req.mentor_id != mentor_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reject this request.",
        )

    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject a request with status '{req.status.value}'. Only pending requests can be rejected.",
        )

    req.status = RequestStatus.REJECTED
    req.rejection_reason = rejection_reason
    req.responded_at = func.now()
    db.commit()
    db.refresh(req)

    mentor_user = db.query(User).filter(User.id == mentor_user_id).first()
    founder_user = db.query(User).filter(User.id == req.founder_id).first()

    return _build_full_response(req, mentor_user, founder_user)


# ---------------------------------------------------------------------------
# Status check (Founder, for a specific mentor)
# ---------------------------------------------------------------------------

def check_request_status(
    db: Session,
    founder_id: int,
    mentor_profile_id: int,
) -> MentorshipCheckResponse:
    """Quick check whether the founder has a pending request or active mentorship."""
    pending = (
        db.query(MentorshipRequest)
        .filter(
            MentorshipRequest.founder_id == founder_id,
            MentorshipRequest.mentor_id == mentor_profile_id,
            MentorshipRequest.status == RequestStatus.PENDING,
        )
        .first()
    )

    active = (
        db.query(Mentorship)
        .filter(
            Mentorship.founder_id == founder_id,
            Mentorship.mentor_id == mentor_profile_id,
            Mentorship.status == MentorshipStatus.ACTIVE,
        )
        .first()
    )

    return MentorshipCheckResponse(
        has_pending_request=pending is not None,
        has_active_mentorship=active is not None,
        pending_request_id=pending.id if pending else None,
        mentorship_id=active.id if active else None,
    )
