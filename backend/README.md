# VentureAI — Auth Backend

FastAPI + PostgreSQL authentication service for the VentureAI platform (Founder / Mentor / Admin roles, JWT-in-HttpOnly-cookie sessions, RBAC).

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL to your PostgreSQL instance, generate a real JWT_SECRET_KEY
```

Create the database, then start the app once to auto-create tables:

```bash
uvicorn app.main:app --reload
```

Seed the three roles (required before anyone can register):

```bash
python -m app.seed
```

API docs available at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create a Founder or Mentor account |
| POST | `/auth/login` | No | Verify credentials, set access + refresh cookies |
| GET | `/auth/me` | Yes | Get the current logged-in user |
| POST | `/auth/logout` | No | Clear auth cookies |
| POST | `/auth/refresh` | Refresh cookie | Exchange refresh token for a new access token |

Admin accounts are **not** publicly registrable — insert them directly via the DB or an internal script, e.g.:

```python
from app.database.connection import SessionLocal
from app.users.models import User, Role
from app.auth.jwt import hash_password

db = SessionLocal()
admin_role = db.query(Role).filter(Role.name == "Admin").first()
db.add(User(name="Admin", email="admin@ventureai.com",
            password_hash=hash_password("SomeStrong!Pass1"), role_id=admin_role.id))
db.commit()
```

## Protecting a route by role

```python
from fastapi import Depends
from app.auth.dependencies import require_role

@router.get("/admin/dashboard")
def admin_dashboard(user = Depends(require_role("Admin"))):
    ...
```

A Founder hitting this route gets `403 Forbidden`, matching the spec.

## Notes

- Passwords are hashed with bcrypt (`passlib`), never stored in plaintext.
- Access tokens expire in 15 minutes, refresh tokens in 7 days — both configurable via `.env`.
- Both tokens are set as `HttpOnly`, `SameSite=Strict` cookies. Set `COOKIE_SECURE=true` in production (HTTPS only).
- `Base.metadata.create_all()` handles first-run table creation; swap in Alembic migrations for real schema evolution.

## Local dev gotcha: use matching hostnames

Browsers treat `localhost` and `127.0.0.1` as **different sites**, even on the same machine. If your frontend is served on one and `API_BASE_URL` in `frontend/js/auth.js` points at the other, the `SameSite=Strict` auth cookies get silently dropped — login will appear to succeed (`200` from `/auth/login`) but `/auth/me` will keep returning `401` and the dashboard will never unlock.

Fix: serve both on the same hostname, e.g.:

```bash
# backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# frontend (from the frontend/ folder)
python -m http.server 8080 --bind 127.0.0.1   # then visit http://localhost:8080, not http://127.0.0.1:8080
```

and make sure `CORS_ORIGINS` in `.env` and `API_BASE_URL` in `auth.js` both reference `localhost` (or both `127.0.0.1`) consistently.
