"""
Mentorship Request API routes.

  POST   /mentorship/requests                 -> create a mentorship request (Founder)
  GET    /mentorship/requests/sent            -> founder's sent requests
  GET    /mentorship/requests/received        -> mentor's incoming requests
  GET    /mentorship/requests/check/{mentor_id} -> quick status check (Founder)
  GET    /mentorship/requests/{id}            -> request detail (Founder or Mentor)
  PATCH  /mentorship/requests/{id}/cancel     -> cancel pending request (Founder)
  PATCH  /mentorship/requests/{id}/accept     -> accept pending request (Mentor)
  PATCH  /mentorship/requests/{id}/reject     -> reject pending request (Mentor)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User, MentorProfile
from app.auth.dependencies import require_role, get_current_user
from app.mentorship.schemas import (
    MentorshipRequestCreate,
    MentorshipRequestResponse,
    MentorshipRequestReject,
    MentorshipRequestListResponse,
    MentorshipCheckResponse,
)
from app.mentorship import service

router = APIRouter(prefix="/mentorship", tags=["Mentorship"])


# -----------------------------------------------------------------------
# Founder: create request
# -----------------------------------------------------------------------

@router.post("/requests", response_model=MentorshipRequestResponse, status_code=201)
def create_request(
    payload: MentorshipRequestCreate,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Create a mentorship request from the authenticated founder to a mentor."""
    return service.create_request(db, current_user.id, payload)


# -----------------------------------------------------------------------
# Founder: list sent requests
# -----------------------------------------------------------------------

@router.get("/requests/sent", response_model=MentorshipRequestListResponse)
def get_sent_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return paginated list of mentorship requests sent by this founder."""
    return service.get_founder_requests(db, current_user.id, page, limit)


# -----------------------------------------------------------------------
# Mentor: list received requests
# -----------------------------------------------------------------------

@router.get("/requests/received", response_model=MentorshipRequestListResponse)
def get_received_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(require_role("Mentor")),
    db: Session = Depends(get_db),
):
    """Return paginated list of mentorship requests addressed to this mentor."""
    profile = (
        db.query(MentorProfile)
        .filter(MentorProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        return {
            "requests": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
        }
    return service.get_mentor_requests(db, profile.id, page, limit, status_filter)


# -----------------------------------------------------------------------
# Founder: quick status check for a mentor
# -----------------------------------------------------------------------

@router.get("/requests/check/{mentor_id}", response_model=MentorshipCheckResponse)
def check_mentor_status(
    mentor_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Check if the founder has a pending request or active mentorship with this mentor."""
    return service.check_request_status(db, current_user.id, mentor_id)


# -----------------------------------------------------------------------
# Request detail (both roles)
# -----------------------------------------------------------------------

@router.get("/requests/{request_id}", response_model=MentorshipRequestResponse)
def get_request_detail(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return full detail for a single mentorship request. Ownership is verified."""
    return service.get_request_detail(db, request_id, current_user)


# -----------------------------------------------------------------------
# Founder: cancel request
# -----------------------------------------------------------------------

@router.patch("/requests/{request_id}/cancel", response_model=MentorshipRequestResponse)
def cancel_request(
    request_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Cancel a pending mentorship request. Only the creating founder can cancel."""
    return service.cancel_request(db, request_id, current_user.id)


# -----------------------------------------------------------------------
# Mentor: accept request
# -----------------------------------------------------------------------

@router.patch("/requests/{request_id}/accept", response_model=MentorshipRequestResponse)
def accept_request(
    request_id: int,
    current_user: User = Depends(require_role("Mentor")),
    db: Session = Depends(get_db),
):
    """Accept a pending mentorship request. Only the addressed mentor can accept."""
    return service.accept_request(db, request_id, current_user.id)


# -----------------------------------------------------------------------
# Mentor: reject request
# -----------------------------------------------------------------------

@router.patch("/requests/{request_id}/reject", response_model=MentorshipRequestResponse)
def reject_request(
    request_id: int,
    payload: MentorshipRequestReject = MentorshipRequestReject(),
    current_user: User = Depends(require_role("Mentor")),
    db: Session = Depends(get_db),
):
    """Reject a pending mentorship request. Only the addressed mentor can reject."""
    return service.reject_request(
        db, request_id, current_user.id, payload.rejection_reason
    )
