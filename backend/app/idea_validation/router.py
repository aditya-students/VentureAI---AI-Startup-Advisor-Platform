"""
Idea Validation API routes.

  POST /startups/{startup_id}/idea-validation         -> run validation
  GET  /startups/{startup_id}/idea-validation/latest   -> latest report
  GET  /startups/{startup_id}/idea-validation/history  -> version history
  GET  /startups/{startup_id}/idea-validation/{validation_id} -> specific report
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.idea_validation.schemas import (
    ValidationReportResponse,
    ValidationHistoryItem,
)
from app.idea_validation import service

router = APIRouter(prefix="/startups", tags=["Idea Validation"])


@router.post(
    "/{startup_id}/idea-validation",
    response_model=ValidationReportResponse,
)
async def run_idea_validation(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Run the AI Idea Validation pipeline for the founder's startup.

    Creates a new versioned validation report each time.
    The pipeline:
    1. Extracts the Leap-of-Faith Assumption (LOFA)
    2. Runs three parallel Red-Team agents (VC, Buyer, Competitor)
    3. Synthesizes all perspectives
    4. Applies deterministic scoring with veto penalties
    5. Generates a falsification blueprint

    Returns the complete validation report.
    """
    return await service.run_validation(db, startup_id, current_user.id)


@router.get(
    "/{startup_id}/idea-validation/latest",
    response_model=ValidationReportResponse,
)
def get_latest_validation(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the latest validation report for the founder's startup."""
    return service.get_latest_validation(db, startup_id, current_user.id)


@router.get(
    "/{startup_id}/idea-validation/history",
    response_model=list[ValidationHistoryItem],
)
def get_validation_history(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return all validation versions (lightweight) for the founder's startup."""
    return service.get_validation_history(db, startup_id, current_user.id)


@router.get(
    "/{startup_id}/idea-validation/{validation_id}",
    response_model=ValidationReportResponse,
)
def get_validation_by_id(
    startup_id: int,
    validation_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return a specific validation report by ID."""
    return service.get_validation_by_id(db, startup_id, validation_id, current_user.id)
