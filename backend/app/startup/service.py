"""
Startup business logic — kept separate from the router so route
handlers stay thin and this logic is independently testable.
"""

from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.startup.models import Startup, StartupStatus
from app.startup.schemas import StartupCreate, StartupUpdate


def get_startup_by_founder(db: Session, founder_id: int) -> Optional[Startup]:
    """Load the startup for a given founder. Returns None if not found."""
    return db.query(Startup).filter(Startup.founder_id == founder_id).first()


def create_startup(db: Session, founder_id: int, data: StartupCreate) -> Startup:
    """
    Create a startup for the given founder.
    Enforces the one-founder/one-startup constraint at the application level
    (the DB unique constraint is the ultimate safety net).
    """
    existing = get_startup_by_founder(db, founder_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a startup. Each founder can have one startup.",
        )

    startup = Startup(
        founder_id=founder_id,
        name=data.name,
        tagline=data.tagline,
        problem=data.problem,
        solution=data.solution,
        industry=data.industry,
        target_market=data.target_market,
        stage=data.stage,
    )
    db.add(startup)
    db.commit()
    db.refresh(startup)
    return startup


def update_startup(db: Session, founder_id: int, data: StartupUpdate) -> Startup:
    """Update editable startup fields and persist the changes."""
    startup = get_startup_by_founder(db, founder_id)
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(startup, field, value)

    db.commit()
    db.refresh(startup)
    return startup


def update_startup_status(
    db: Session, founder_id: int, new_status: StartupStatus
) -> Startup:
    """Change the startup's status (archive/restore)."""
    startup = get_startup_by_founder(db, founder_id)
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Startup not found.",
        )

    startup.status = new_status
    db.commit()
    db.refresh(startup)
    return startup
