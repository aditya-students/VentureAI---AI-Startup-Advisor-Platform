"""
Startup Workspace API routes.

  POST  /startups         -> create a startup for the current founder
  GET   /startups/me      -> return the current founder's startup
  PUT   /startups/me      -> update startup information
  PATCH /startups/me/status -> archive or restore a startup
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.startup.schemas import (
    StartupCreate,
    StartupUpdate,
    StartupStatusUpdate,
    StartupResponse,
)
from app.startup import service

router = APIRouter(prefix="/startups", tags=["Startup"])


def _startup_to_response(startup) -> StartupResponse:
    """Convert a Startup ORM instance to a response schema."""
    return StartupResponse(
        id=startup.id,
        founder_id=startup.founder_id,
        name=startup.name,
        tagline=startup.tagline,
        problem=startup.problem,
        solution=startup.solution,
        industry=startup.industry,
        target_market=startup.target_market,
        stage=startup.stage.value,
        status=startup.status.value,
        created_at=startup.created_at,
        updated_at=startup.updated_at,
    )


@router.post("", response_model=StartupResponse, status_code=status.HTTP_201_CREATED)
def create_startup(
    payload: StartupCreate,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Create a startup for the currently authenticated Founder.
    The founder_id is derived from the JWT — never from client input.
    """
    startup = service.create_startup(db, current_user.id, payload)
    return _startup_to_response(startup)


@router.get("/me", response_model=StartupResponse)
def get_my_startup(
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the authenticated founder's startup, or 404 if none exists."""
    startup = service.get_startup_by_founder(db, current_user.id)
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't created a startup yet.",
        )
    return _startup_to_response(startup)


@router.put("/me", response_model=StartupResponse)
def update_my_startup(
    payload: StartupUpdate,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Update the current founder's startup information."""
    startup = service.update_startup(db, current_user.id, payload)
    return _startup_to_response(startup)


@router.patch("/me/status", response_model=StartupResponse)
def update_startup_status(
    payload: StartupStatusUpdate,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Archive or restore the current founder's startup."""
    startup = service.update_startup_status(db, current_user.id, payload.status)
    return _startup_to_response(startup)
