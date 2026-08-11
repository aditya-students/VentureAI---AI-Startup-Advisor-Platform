"""
VentureAI backend — FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload

On startup this creates any missing tables (roles, users). It does NOT
seed role data automatically — run `python -m app.seed` once after your
first migration/table creation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.connection import engine
from app.database.base import Base

# Import models so their table definitions are registered on Base.metadata
# before create_all() runs. (Unused import, but required for side effects.)
from app.users import models as _users_models  # noqa: F401
from app.startup import models as _startup_models  # noqa: F401
from app.idea_validation import models as _validation_models  # noqa: F401

from app.auth.router import router as auth_router
from app.founder.router import router as founder_router
from app.startup.router import router as startup_router
from app.idea_validation.router import router as validation_router

app = FastAPI(
    title="VentureAI API",
    description="Authentication + core API for the VentureAI AI Startup Advisor platform.",
    version="1.0.0",
)

# --- CORS ---
# allow_credentials=True is required so the browser sends/receives the
# HttpOnly auth cookies on cross-origin requests from the frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_router)
app.include_router(founder_router)
app.include_router(startup_router)
app.include_router(validation_router)


@app.on_event("startup")
def on_startup():
    # Creates tables if they don't exist yet. For real schema evolution,
    # swap this for Alembic migrations — create_all() only handles first-run setup.
    Base.metadata.create_all(bind=engine)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "VentureAI API"}
