"""
Shared SQLAlchemy declarative base.

Kept in its own module (separate from connection.py) so model files
(app/users/models.py, etc.) can import `Base` without pulling in the
engine/session — avoids circular imports.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
