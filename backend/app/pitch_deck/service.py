"""
Service layer for AI Pitch Deck Generator.

Handles:
- Founder workspace ownership verification
- Upstream prerequisite validation & context retrieval
- Full pitch deck generation pipeline
- Version management (incrementing versions, preserving previous runs)
- Single slide editing & single slide regeneration
- Report retrieval & version history
- PDF HTML presentation layout builder
"""

import asyncio
from copy import deepcopy
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.startup.models import Startup
from app.pitch_deck.models import PitchDeck
from app.pitch_deck.context import get_prerequisites_status, build_pitch_deck_context
from app.pitch_deck.graph.graph import run_pitch_deck_pipeline
from app.pitch_deck.graph.nodes import regenerate_single_slide_node, run_pitch_deck_audit


def _verify_startup_ownership(db: Session, startup_id: int, user_id: int) -> Startup:
    """Ensure startup workspace exists and belongs to the authenticated founder."""
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Startup workspace with ID {startup_id} not found.",
        )
    if startup.founder_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this startup workspace.",
        )
    return startup


def check_prerequisites(db: Session, startup_id: int, user_id: int) -> Dict[str, Any]:
    """Check status of upstream prerequisites before pitch deck generation."""
    _verify_startup_ownership(db, startup_id, user_id)
    return get_prerequisites_status(db, startup_id)


async def generate_pitch_deck(db: Session, startup_id: int, user_id: int) -> PitchDeck:
    """Generate a complete new 13-slide AI Pitch Deck version."""
    _verify_startup_ownership(db, startup_id, user_id)

    # 1. Build Context
    try:
        context = build_pitch_deck_context(db, startup_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 2. Run Generation Pipeline
    pipeline_result = await run_pitch_deck_pipeline(context)

    # 3. Determine next version number
    latest = (
        db.query(PitchDeck)
        .filter(PitchDeck.startup_id == startup_id)
        .order_by(PitchDeck.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else 1

    # 4. Save Version in DB
    val_data = context.get("validation_data", {})
    bmc_data = context.get("bmc_data", {})
    bp_data = context.get("business_plan_data", {})

    deck_record = PitchDeck(
        startup_id=startup_id,
        validation_report_id=val_data.get("id"),
        bmc_version_id=bmc_data.get("id"),
        business_plan_id=bp_data.get("id"),
        version_number=next_version,
        slides_data=pipeline_result["slides_data"],
        audit_report=pipeline_result["audit_report"],
        is_validation_mode=pipeline_result["is_validation_mode"],
        validation_score=pipeline_result["validation_score"],
    )
    db.add(deck_record)
    db.commit()
    db.refresh(deck_record)
    return deck_record


def get_latest_pitch_deck(db: Session, startup_id: int, user_id: int) -> PitchDeck:
    """Fetch the latest Pitch Deck version for the startup workspace."""
    _verify_startup_ownership(db, startup_id, user_id)

    latest = (
        db.query(PitchDeck)
        .filter(PitchDeck.startup_id == startup_id)
        .order_by(PitchDeck.version_number.desc())
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Pitch Deck has been generated yet for this startup workspace.",
        )
    return latest


def get_pitch_deck_history(db: Session, startup_id: int, user_id: int) -> List[PitchDeck]:
    """Fetch all Pitch Deck versions for the startup."""
    _verify_startup_ownership(db, startup_id, user_id)

    return (
        db.query(PitchDeck)
        .filter(PitchDeck.startup_id == startup_id)
        .order_by(PitchDeck.version_number.desc())
        .all()
    )


def get_pitch_deck_by_id(db: Session, deck_id: int, user_id: int) -> PitchDeck:
    """Fetch a specific Pitch Deck by ID after owner verification."""
    deck = db.query(PitchDeck).filter(PitchDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pitch Deck with ID {deck_id} not found.",
        )
    _verify_startup_ownership(db, deck.startup_id, user_id)
    return deck


async def edit_slide(
    db: Session,
    deck_id: int,
    slide_number: int,
    edit_data: Dict[str, Any],
    user_id: int
) -> PitchDeck:
    """Updates fields on a single slide, re-audits deck, and saves as a new version."""
    current_deck = get_pitch_deck_by_id(db, deck_id, user_id)
    startup_id = current_deck.startup_id

    slides = deepcopy(current_deck.slides_data)
    target = next((s for s in slides if s.get("slide_number") == slide_number), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slide number {slide_number} does not exist in this deck.",
        )

    if edit_data.get("title") is not None:
        target["title"] = edit_data["title"]
    if edit_data.get("subtitle") is not None:
        target["subtitle"] = edit_data["subtitle"]
    if edit_data.get("content") is not None:
        target["content"] = edit_data["content"]
    if edit_data.get("key_points") is not None:
        target["key_points"] = edit_data["key_points"]

    context = build_pitch_deck_context(db, startup_id)
    new_audit = await asyncio.to_thread(run_pitch_deck_audit, context, slides)

    latest = (
        db.query(PitchDeck)
        .filter(PitchDeck.startup_id == startup_id)
        .order_by(PitchDeck.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else (current_deck.version_number + 1)

    new_version = PitchDeck(
        startup_id=startup_id,
        validation_report_id=current_deck.validation_report_id,
        bmc_version_id=current_deck.bmc_version_id,
        business_plan_id=current_deck.business_plan_id,
        version_number=next_version,
        slides_data=slides,
        audit_report=new_audit,
        is_validation_mode=current_deck.is_validation_mode,
        validation_score=current_deck.validation_score,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


async def regenerate_slide(
    db: Session,
    deck_id: int,
    slide_number: int,
    custom_instructions: Optional[str],
    user_id: int
) -> PitchDeck:
    """Regenerates a single slide with AI, re-audits deck, and saves as a new version."""
    current_deck = get_pitch_deck_by_id(db, deck_id, user_id)
    startup_id = current_deck.startup_id

    context = build_pitch_deck_context(db, startup_id)
    slides = deepcopy(current_deck.slides_data)

    target_idx = next((i for i, s in enumerate(slides) if s.get("slide_number") == slide_number), None)
    if target_idx is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slide number {slide_number} does not exist in this deck.",
        )

    new_slide = await asyncio.to_thread(
        regenerate_single_slide_node, slide_number, context, slides, custom_instructions
    )
    slides[target_idx] = new_slide

    new_audit = await asyncio.to_thread(run_pitch_deck_audit, context, slides)

    latest = (
        db.query(PitchDeck)
        .filter(PitchDeck.startup_id == startup_id)
        .order_by(PitchDeck.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else (current_deck.version_number + 1)

    new_version = PitchDeck(
        startup_id=startup_id,
        validation_report_id=current_deck.validation_report_id,
        bmc_version_id=current_deck.bmc_version_id,
        business_plan_id=current_deck.business_plan_id,
        version_number=next_version,
        slides_data=slides,
        audit_report=new_audit,
        is_validation_mode=current_deck.is_validation_mode,
        validation_score=current_deck.validation_score,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


import json
import re

def _sanitize_text_py(input_val: Any) -> str:
    if input_val is None:
        return ""
    if isinstance(input_val, dict):
        if "items" in input_val and isinstance(input_val["items"], list):
            return _sanitize_text_py(input_val["items"])
        if "title" in input_val or "desc" in input_val or "label" in input_val:
            parts = [input_val.get("title"), input_val.get("desc") or input_val.get("label")]
            return ": ".join([str(p) for p in parts if p])
        clean_vals = []
        for k, v in input_val.items():
            if k in ['risk_notes', 'last_updated', 'generated_by_ai', 'modified_by_founder', 'id', 'created_at']:
                continue
            if v:
                clean_vals.append(_sanitize_text_py(v))
        return " • ".join(clean_vals)
    if isinstance(input_val, list):
        return " • ".join([_sanitize_text_py(item) for item in input_val if _sanitize_text_py(item)])

    if isinstance(input_val, str):
        s = input_val.strip()
        if "{" in s and "}" in s:
            def replace_items_dict(match):
                items_str = match.group(1)
                items = [re.sub(r"^['\"\s]+|['\"\s]+$", "", it) for it in items_str.split(",") if it.strip()]
                return ", ".join(items)

            s = re.sub(r"\{[^{}]*['\"]items['\"]\s*:\s*\[([^\]]+)\][^{}]*\}", replace_items_dict, s, flags=re.IGNORECASE)

            if s.startswith("{") and s.endswith("}"):
                try:
                    json_str = s.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")
                    parsed = json.loads(json_str)
                    return _sanitize_text_py(parsed)
                except Exception:
                    s = re.sub(r"'risk_notes':\s*None,?", "", s, flags=re.IGNORECASE)
                    s = re.sub(r"'last_updated':\s*'[^']+',?", "", s, flags=re.IGNORECASE)
                    s = re.sub(r"'generated_by_ai':\s*(True|False),?", "", s, flags=re.IGNORECASE)
                    s = re.sub(r"'modified_by_founder':\s*(True|False),?", "", s, flags=re.IGNORECASE)
                    s = re.sub(r"['\"]items['\"]:\s*", "", s, flags=re.IGNORECASE)
                    s = re.sub(r"[{}'\"]", "", s)

        s = re.sub(r"'risk_notes':\s*None,?", "", s, flags=re.IGNORECASE)
        s = re.sub(r"'last_updated':\s*'[^']+',?", "", s, flags=re.IGNORECASE)
        s = re.sub(r"'generated_by_ai':\s*(True|False),?", "", s, flags=re.IGNORECASE)
        s = re.sub(r"'modified_by_founder':\s*(True|False),?", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    return str(input_val)


def _parse_hero_stat_py(text: str) -> Optional[Dict[str, str]]:
    clean = _sanitize_text_py(text)
    if not clean:
        return None

    if re.match(r"^\d{4}-\d{2}-\d{2}", clean) or "last_updated" in clean.lower():
        return None

    match = re.search(r"(\$\d+(?:\.\d+)?[kMB]?|\d+(?:\.\d+)?%|\b\d+(?:\.\d+)?x\b|\b\d+s\b|\$\d+k?)", clean, re.IGNORECASE)
    if match and match.group(0) and 2 <= len(match.group(0)) <= 10:
        num = match.group(0)
        if re.match(r"^\d{4}$", num):
            return None
        label = clean.replace(num, "")
        label = re.sub(r"^[:\-\s\•\(\)]+", "", label)
        label = re.sub(r"[\(\)]+$", "", label).strip()
        if len(label) >= 3:
            return {"num": num, "label": label}
    return None


def _get_lucide_svg_py(name: str, color: str = "#38BDF8", size: int = 20) -> str:
    n = (name or "").lower()
    svg_open = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle;">'
    svg_close = '</svg>'

    inner = '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'

    if any(k in n for k in ['shield', 'lock', 'moat', 'secu', 'defens']):
        inner = '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>'
    elif any(k in n for k in ['user', 'customer', 'people', 'team', 'ask']):
        inner = '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    elif any(k in n for k in ['trend', 'growth', 'chart', 'up', 'unit', 'econ']):
        inner = '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>'
    elif any(k in n for k in ['data', 'server', 'layer', 'workflow', 'product']):
        inner = '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
    elif any(k in n for k in ['rocket', 'launch', 'speed', 'gtm', 'go-to']):
        inner = '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-3.05 11a22.35 22.35 0 0 1-3.95 2z"/><path d="M9 20l-4 4"/><path d="M14.5 9.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>'
    elif any(k in n for k in ['dollar', 'money', 'coin', 'rev', 'business', 'model', 'cost']):
        inner = '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
    elif any(k in n for k in ['award', 'star', 'trophy', 'crown', 'compet']):
        inner = '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>'
    elif any(k in n for k in ['check', 'valid', 'tract', 'done']):
        inner = '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
    elif any(k in n for k in ['target', 'aim', 'market', 'opp']):
        inner = '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'
    elif any(k in n for k in ['zap', 'bolt', 'flash', 'speed']):
        inner = '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
    elif any(k in n for k in ['clock', 'time', 'why', 'now']):
        inner = '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
    elif any(k in n for k in ['light', 'bulb', 'solu', 'idea']):
        inner = '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1.3.5 2.6 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>'
    elif any(k in n for k in ['problem', 'alert', 'warn', 'issue']):
        inner = '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 1 1.73-3z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
    elif any(k in n for k in ['sparkle', 'gem', 'cover']):
        inner = '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3z"/>'

    return svg_open + inner + svg_close


def export_pdf_html(db: Session, deck_id: int, user_id: int) -> str:
    """Generates a standalone 16:9 printable HTML presentation for PDF export."""
    deck = get_pitch_deck_by_id(db, deck_id, user_id)
    startup = db.query(Startup).filter(Startup.id == deck.startup_id).first()
    startup_name = startup.name if startup else "Startup Workspace"

    slides_html = ""
    for slide in deck.slides_data:
        s_num = slide.get("slide_number", 1)
        s_num_str = f"0{s_num}" if s_num < 10 else str(s_num)
        s_type = (slide.get("slide_type") or "").upper()
        title = _sanitize_text_py(slide.get("title"))
        subtitle = _sanitize_text_py(slide.get("subtitle"))
        content = _sanitize_text_py(slide.get("content"))
        raw_kps = slide.get("key_points", [])

        icon_svg = _get_lucide_svg_py(slide.get("slide_type") or slide.get("icon_name") or "sparkles", "#38BDF8", 22)

        page_break = "avoid" if s_num == 13 else "always"
        break_after = "avoid" if s_num == 13 else "page"

        # Component 1: Cover Slide
        if s_num == 1 or slide.get("slide_type") == "cover":
            kp_cards = ""
            for kp in raw_kps:
                stat = _parse_hero_stat_py(kp)
                clean_kp = _sanitize_text_py(kp)
                if stat:
                    kp_cards += f"""
                    <div style="background:#151C2C;border:1px solid #232D42;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:6px;">
                      <span style="font-size:2rem;font-weight:800;color:#38BDF8;letter-spacing:-0.02em;">{stat['num']}</span>
                      <span style="font-size:0.85rem;color:#94A3B8;line-height:1.4;">{stat['label']}</span>
                    </div>
                    """
                else:
                    kp_icon = _get_lucide_svg_py("sparkles", "#38BDF8", 18)
                    kp_cards += f"""
                    <div style="background:#151C2C;border:1px solid #232D42;border-radius:12px;padding:16px;display:flex;align-items:flex-start;gap:10px;font-size:0.9rem;color:#E2E8F0;">
                      <span style="margin-top:2px;">{kp_icon}</span>
                      <span>{clean_kp}</span>
                    </div>
                    """

            slides_html += f"""
            <div class="pdf-slide-canvas" style="width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden; background: radial-gradient(circle at 85% 15%, rgba(56, 189, 248, 0.15) 0%, transparent 55%), radial-gradient(circle at 15% 85%, rgba(168, 85, 247, 0.12) 0%, transparent 55%), #151C2C; color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex; flex-direction: column; justify-content: space-between; page-break-after: {page_break}; break-after: {break_after}; page-break-inside: avoid; break-inside: avoid; margin: 0;">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                  <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
                    {icon_svg}
                    <span>SLIDE 01 / 13</span>
                  </span>
                  <span style="background:rgba(56,189,248,0.12);color:#38BDF8;border:1px solid rgba(56,189,248,0.3);padding:4px 14px;border-radius:20px;font-size:0.75rem;font-weight:700;">
                    INVESTOR PITCH DECK
                  </span>
                </div>
                <div style="margin-bottom:24px;">
                  <h1 style="font-size:2.4rem;font-weight:900;color:#FFF;line-height:1.15;margin:0 0 10px 0;">{title}</h1>
                  <div style="font-size:1.15rem;font-weight:600;color:#38BDF8;margin-bottom:16px;">{subtitle}</div>
                  <div style="background:rgba(11,15,25,0.6);border:1px solid #232D42;border-radius:14px;padding:18px 22px;font-size:1rem;line-height:1.6;color:#CBD5E1;">
                    {content}
                  </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:12px;">
                  {kp_cards}
                </div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
                <span>VentureAI AI Pitch Deck Generator</span>
                <span>{startup_name}</span>
              </div>
            </div>
            """
        # Component 2: Product Workflow Timeline Pipeline (Slide 6)
        elif s_num == 6 or slide.get("slide_type") == "product_workflow" or slide.get("visual_type") == "three_step_flow":
            steps = [
                {"step": 1, "title": "Context Ingestion", "desc": "Securely ingests startup profile & validation data."},
                {"step": 2, "title": "AI Engine Execution", "desc": "Runs multi-agent Zero-Trust compliance & risk scoring."},
                {"step": 3, "title": "Audit & Output", "desc": "Generates investor-ready presentation decks in seconds."}
            ]
            if slide.get("visual_data") and isinstance(slide["visual_data"].get("steps"), list):
                steps = [
                    {
                        "step": st.get("step") or st.get("step_number") or i+1,
                        "title": _sanitize_text_py(st.get("title") or st.get("step_title") or "Step"),
                        "desc": _sanitize_text_py(st.get("desc") or st.get("description") or "")
                    }
                    for i, st in enumerate(slide["visual_data"]["steps"])
                ]

            pipeline_cards = ""
            for idx, st in enumerate(steps):
                pipeline_cards += f"""
                <div style="background:#0B0F19;border:1px solid #232D42;border-radius:14px;padding:18px;text-align:center;">
                  <div style="width:32px;height:32px;border-radius:50%;background:#38BDF8;color:#0B0F19;font-weight:900;display:flex;align-items:center;justify-content:center;margin:0 auto 10px;font-size:0.9rem;">{st['step']}</div>
                  <div style="font-weight:700;color:#FFF;margin-bottom:6px;font-size:0.95rem;">{st['title']}</div>
                  <div style="font-size:0.82rem;color:#94A3B8;line-height:1.4;">{st['desc']}</div>
                </div>
                """
                if idx < len(steps) - 1:
                    pipeline_cards += '<div style="color:#38BDF8;font-size:1.6rem;font-weight:800;text-align:center;align-self:center;">➔</div>'

            slides_html += f"""
            <div class="pdf-slide-canvas" style="width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden; background: #151C2C; color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex; flex-direction: column; justify-content: space-between; page-break-after: {page_break}; break-after: {break_after}; page-break-inside: avoid; break-inside: avoid; margin: 0;">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                  <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
                    {icon_svg}
                    <span>SLIDE 06 / 13</span>
                  </span>
                  <span style="background:rgba(255,255,255,0.06);color:#CBD5E1;padding:4px 12px;border-radius:12px;font-size:0.75rem;font-weight:600;">
                    PRODUCT WORKFLOW
                  </span>
                </div>
                <h2 style="font-size:1.85rem;font-weight:800;color:#FFF;line-height:1.2;margin:0 0 6px 0;">{title}</h2>
                <h3 style="font-size:1.05rem;font-weight:500;color:#94A3B8;margin:0 0 16px 0;line-height:1.35;">{subtitle}</h3>
                <p style="font-size:0.95rem;line-height:1.55;color:#E2E8F0;margin-bottom:20px;">{content}</p>

                <div style="background:#151C2C;border:1px solid #232D42;border-radius:16px;padding:22px;margin-bottom:16px;">
                  <div style="display:grid;grid-template-columns:{'1fr auto 1fr auto 1fr' if len(steps) == 3 else 'repeat(auto-fit, minmax(200px, 1fr))'};align-items:center;gap:14px;">
                    {pipeline_cards}
                  </div>
                </div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
                <span>VentureAI AI Pitch Deck Generator</span>
                <span>{startup_name}</span>
              </div>
            </div>
            """
        # Component 3 & 4: Standard Frosted Glass Cards & Stat Highlight Slides
        else:
            kps_cards = ""
            for kp in raw_kps:
                stat = _parse_hero_stat_py(kp)
                clean_kp = _sanitize_text_py(kp)
                if stat:
                    kps_cards += f"""
                    <div style="background:#151C2C;border:1px solid #232D42;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:6px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:2.1rem;font-weight:800;color:#38BDF8;letter-spacing:-0.02em;">{stat['num']}</span>
                        <span>{_get_lucide_svg_py(slide.get('slide_type') or 'check-circle', '#38BDF8', 18)}</span>
                      </div>
                      <p style="font-size:0.86rem;color:#94A3B8;line-height:1.4;margin:0;">{stat['label']}</p>
                    </div>
                    """
                else:
                    kp_icon = _get_lucide_svg_py(slide.get('slide_type') or 'check-circle', '#38BDF8', 18)
                    kps_cards += f"""
                    <div style="background:#151C2C;border:1px solid #232D42;border-radius:14px;padding:18px;display:flex;align-items:flex-start;gap:12px;font-size:0.9rem;color:#F1F5F9;line-height:1.45;">
                      <span style="margin-top:2px;">{kp_icon}</span>
                      <span>{clean_kp}</span>
                    </div>
                    """

            warnings_badge = ""
            if slide.get("warnings"):
                warn_icon = _get_lucide_svg_py("alert-triangle", "#FCD34D", 16)
                warn_text = _sanitize_text_py(slide["warnings"][0])
                warnings_badge = f"""
                <div style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);color:#FCD34D;padding:8px 14px;border-radius:10px;font-size:0.85rem;margin-bottom:18px;display:flex;align-items:center;gap:8px;">
                  {warn_icon}
                  <span>{warn_text}</span>
                </div>
                """

            slides_html += f"""
            <div class="pdf-slide-canvas" style="width: 297mm; height: 165mm; max-height: 165mm; box-sizing: border-box; overflow: hidden; background: #151C2C; color: #F8FAFC; padding: 16mm 20mm; position: relative; display: flex; flex-direction: column; justify-content: space-between; page-break-after: {page_break}; break-after: {break_after}; page-break-inside: avoid; break-inside: avoid; margin: 0;">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                  <span style="color:#38BDF8;font-weight:700;font-size:0.85rem;letter-spacing:0.08em;display:flex;align-items:center;gap:8px;">
                    {icon_svg}
                    <span>SLIDE {s_num_str} / 13</span>
                  </span>
                  <span style="background:rgba(255,255,255,0.06);color:#CBD5E1;padding:4px 12px;border-radius:12px;font-size:0.75rem;font-weight:600;">
                    {s_type}
                  </span>
                </div>
                <h2 style="font-size:1.85rem;font-weight:800;color:#FFF;line-height:1.2;margin:0 0 6px 0;">{title}</h2>
                <h3 style="font-size:1.05rem;font-weight:500;color:#94A3B8;margin:0 0 16px 0;line-height:1.35;">{subtitle}</h3>
                {warnings_badge}
                <div style="font-size:0.95rem;line-height:1.55;color:#E2E8F0;margin-bottom:20px;max-height:140px;overflow:hidden;">{content}</div>

                <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:12px;margin-bottom:20px;">
                  {kps_cards}
                </div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid #232D42;font-size:0.75rem;color:#64748B;">
                <span>VentureAI AI Pitch Deck Generator</span>
                <span>{startup_name}</span>
              </div>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>{startup_name} — Pitch Deck v{deck.version_number}.0</title>
<style>
  @page {{ size: 297mm 167.0625mm; margin: 0; }}
  html, body {{ margin: 0; padding: 0; background: #0B0F19; font-family: 'Inter', system-ui, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
</style>
</head>
<body>
{slides_html}
</body>
</html>
"""
    return html


from app.pitch_deck.pptx_builder import build_pitch_deck_pptx

def export_pptx_file(db: Session, deck_id: int, user_id: int) -> bytes:
    """Generates a native 16:9 PowerPoint (.pptx) presentation deck."""
    deck = get_pitch_deck_by_id(db, deck_id, user_id)
    startup = db.query(Startup).filter(Startup.id == deck.startup_id).first()
    startup_name = startup.name if startup else "Startup Workspace"
    return build_pitch_deck_pptx(deck.slides_data, startup_name)
