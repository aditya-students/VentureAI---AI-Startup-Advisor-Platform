"""
Seeds the `roles` table with the three fixed roles the platform expects:
  1 - Founder
  2 - Mentor
  3 - Admin

Run manually after creating the tables:
    python -m app.seed

Idempotent — safe to run multiple times, it skips roles that already exist.
"""

from app.database.connection import SessionLocal, engine
from app.database.base import Base
from app.users import models as _users_models  # noqa: F401
from app.startup import models as _startup_models  # noqa: F401
from app.users.models import Role, RoleName

ROLE_SEED_DATA = [
    (RoleName.FOUNDER.value, "Builds and manages startup workspaces, runs the AI planning pipeline."),
    (RoleName.MENTOR.value, "Reviews assigned startups and provides feedback to founders."),
    (RoleName.ADMIN.value, "Manages users, mentors, and platform-wide activity."),
]


def seed_roles():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for name, description in ROLE_SEED_DATA:
            exists = db.query(Role).filter(Role.name == name).first()
            if not exists:
                db.add(Role(name=name, description=description))
                print(f"Seeded role: {name}")
            else:
                print(f"Role already exists, skipping: {name}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
