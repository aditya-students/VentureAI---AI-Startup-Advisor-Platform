"""
FastAPI router for AI Pitch Deck Generator endpoints.

Supports:
- POST /startups/{startup_id}/pitch-deck/generate  -> generate complete 13-slide pitch deck
- GET  /startups/{startup_id}/pitch-deck/latest    -> get latest pitch deck version
- GET  /startups/{startup_id}/pitch-deck/versions  -> list version history
- GET  /startups/{startup_id}/pitch-deck/check-prerequisites -> check upstream data completeness
- GET  /pitch-deck/{deck_id}                       -> fetch specific pitch deck by ID
- POST /pitch-deck/{deck_id}/regenerate            -> regenerate full deck
- POST /pitch-deck/{deck_id}/slides/{slide_number}/regenerate -> regenerate single slide
- PATCH /pitch-deck/{deck_id}/slides/{slide_number} -> edit single slide
- POST /pitch-deck/{deck_id}/audit                 -> fetch Red Pen audit report
- GET  /pitch-deck/{deck_id}/export/pdf            -> export PDF printable HTML layout
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.users.models import User
from app.auth.dependencies import require_role
from app.pitch_deck.schemas import (
    PitchDeckResponse,
    PitchDeckHistoryItem,
    PrerequisitesStatusResponse,
    SlideEditPayload,
    SlideRegeneratePayload,
    PitchDeckAuditReport,
)
from app.pitch_deck import service

router = APIRouter(tags=["AI Pitch Deck Generator"])


# ===================================================================
# 1. STARTUP WORKSPACE SCOPED ENDPOINTS
# ===================================================================

@router.get(
    "/startups/{startup_id}/pitch-deck/check-prerequisites",
    response_model=PrerequisitesStatusResponse,
)
def check_prerequisites(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Check status of upstream prerequisites before pitch deck generation."""
    return service.check_prerequisites(db, startup_id, current_user.id)


@router.post(
    "/startups/{startup_id}/pitch-deck/generate",
    response_model=PitchDeckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_pitch_deck(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Generate a complete 13-slide AI Pitch Deck using Startup Workspace, AI Idea Validation,
    AI Business Model Canvas, and AI Business Plan context.
    """
    return await service.generate_pitch_deck(db, startup_id, current_user.id)


@router.get(
    "/startups/{startup_id}/pitch-deck/latest",
    response_model=PitchDeckResponse,
)
def get_latest_pitch_deck(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the latest generated Pitch Deck for the founder's startup workspace."""
    return service.get_latest_pitch_deck(db, startup_id, current_user.id)


@router.get(
    "/startups/{startup_id}/pitch-deck/versions",
    response_model=List[PitchDeckHistoryItem],
)
def get_pitch_deck_versions(
    startup_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return version history for the startup's Pitch Deck."""
    return service.get_pitch_deck_history(db, startup_id, current_user.id)


# ===================================================================
# 2. PITCH DECK ENTITY SCOPED ENDPOINTS
# ===================================================================

@router.get(
    "/pitch-deck/{deck_id}",
    response_model=PitchDeckResponse,
)
def get_pitch_deck_by_id(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return a specific Pitch Deck by its unique ID."""
    return service.get_pitch_deck_by_id(db, deck_id, current_user.id)


@router.post(
    "/pitch-deck/{deck_id}/regenerate",
    response_model=PitchDeckResponse,
)
async def regenerate_full_deck(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Regenerate all 13 slides of an existing pitch deck as a new version."""
    deck = service.get_pitch_deck_by_id(db, deck_id, current_user.id)
    return await service.generate_pitch_deck(db, deck.startup_id, current_user.id)


@router.post(
    "/pitch-deck/{deck_id}/slides/{slide_number}/regenerate",
    response_model=PitchDeckResponse,
)
async def regenerate_slide(
    deck_id: int,
    slide_number: int,
    payload: Optional[SlideRegeneratePayload] = None,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Regenerate a single pitch deck slide (1 to 13).
    Preserves all other 12 slides, re-audits the deck, and saves as a new version.
    """
    custom_inst = payload.custom_instructions if payload else None
    return await service.regenerate_slide(
        db, deck_id, slide_number, custom_inst, current_user.id
    )


@router.patch(
    "/pitch-deck/{deck_id}/slides/{slide_number}",
    response_model=PitchDeckResponse,
)
async def edit_slide(
    deck_id: int,
    slide_number: int,
    payload: SlideEditPayload,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """
    Manually edit text/key points of a single pitch deck slide.
    Re-audits deck and saves as a new version.
    """
    return await service.edit_slide(
        db, deck_id, slide_number, payload.model_dump(exclude_unset=True), current_user.id
    )


@router.post(
    "/pitch-deck/{deck_id}/audit",
    response_model=Dict[str, Any],
)
def get_pitch_deck_audit(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return the Red Pen Audit findings for a pitch deck."""
    deck = service.get_pitch_deck_by_id(db, deck_id, current_user.id)
    return deck.audit_report


@router.get(
    "/pitch-deck/{deck_id}/export/pdf",
)
def export_pdf(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Return printable presentation HTML for PDF export."""
    html_content = service.export_pdf_html(db, deck_id, current_user.id)
    return Response(content=html_content, media_type="text/html")


@router.get(
    "/pitch-deck/{deck_id}/export/pptx",
)
def export_pptx(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Export pitch deck as a downloadable PowerPoint (.pptx) file."""
    pptx_bytes = service.export_pptx_file(db, deck_id, current_user.id)
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=pitch-deck-{deck_id}.pptx"},
    )


# ===================================================================
# 3. DIRECT /api/ PREFIX ALIASES
# ===================================================================

@router.post(
    "/api/pitch-deck/generate",
    response_model=PitchDeckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def api_generate_pitch_deck(
    startup_id: int = Query(..., description="Startup Workspace ID"),
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for POST /startups/{startup_id}/pitch-deck/generate."""
    return await service.generate_pitch_deck(db, startup_id, current_user.id)


@router.get(
    "/api/pitch-deck/{workspace_id}/latest",
    response_model=PitchDeckResponse,
)
def api_get_latest_pitch_deck(
    workspace_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /startups/{startup_id}/pitch-deck/latest."""
    return service.get_latest_pitch_deck(db, workspace_id, current_user.id)


@router.get(
    "/api/pitch-deck/{workspace_id}",
    response_model=PitchDeckResponse,
)
def api_get_pitch_deck_by_workspace(
    workspace_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /startups/{startup_id}/pitch-deck/latest."""
    return service.get_latest_pitch_deck(db, workspace_id, current_user.id)


@router.get(
    "/api/pitch-deck/{workspace_id}/versions",
    response_model=List[PitchDeckHistoryItem],
)
def api_get_pitch_deck_versions(
    workspace_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /startups/{startup_id}/pitch-deck/versions."""
    return service.get_pitch_deck_history(db, workspace_id, current_user.id)


@router.post(
    "/api/pitch-deck/{deck_id}/regenerate",
    response_model=PitchDeckResponse,
)
async def api_regenerate_full_deck(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for POST /pitch-deck/{deck_id}/regenerate."""
    deck = service.get_pitch_deck_by_id(db, deck_id, current_user.id)
    return await service.generate_pitch_deck(db, deck.startup_id, current_user.id)


@router.post(
    "/api/pitch-deck/{deck_id}/slides/{slide_number}/regenerate",
    response_model=PitchDeckResponse,
)
async def api_regenerate_slide(
    deck_id: int,
    slide_number: int,
    payload: Optional[SlideRegeneratePayload] = None,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for POST /pitch-deck/{deck_id}/slides/{slide_number}/regenerate."""
    custom_inst = payload.custom_instructions if payload else None
    return await service.regenerate_slide(
        db, deck_id, slide_number, custom_inst, current_user.id
    )


@router.patch(
    "/api/pitch-deck/{deck_id}/slides/{slide_number}",
    response_model=PitchDeckResponse,
)
async def api_edit_slide(
    deck_id: int,
    slide_number: int,
    payload: SlideEditPayload,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for PATCH /pitch-deck/{deck_id}/slides/{slide_number}."""
    return await service.edit_slide(
        db, deck_id, slide_number, payload.model_dump(exclude_unset=True), current_user.id
    )


@router.post(
    "/api/pitch-deck/{deck_id}/audit",
    response_model=Dict[str, Any],
)
def api_get_pitch_deck_audit(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for POST /pitch-deck/{deck_id}/audit."""
    deck = service.get_pitch_deck_by_id(db, deck_id, current_user.id)
    return deck.audit_report


@router.get(
    "/api/pitch-deck/{deck_id}/export/pdf",
)
def api_export_pdf(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /pitch-deck/{deck_id}/export/pdf."""
    html_content = service.export_pdf_html(db, deck_id, current_user.id)
    return Response(content=html_content, media_type="text/html")


@router.get(
    "/api/pitch-deck/{deck_id}/export/pptx",
)
def api_export_pptx(
    deck_id: int,
    current_user: User = Depends(require_role("Founder")),
    db: Session = Depends(get_db),
):
    """Alias for GET /pitch-deck/{deck_id}/export/pptx."""
    pptx_bytes = service.export_pptx_file(db, deck_id, current_user.id)
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=pitch-deck-{deck_id}.pptx"},
    )
