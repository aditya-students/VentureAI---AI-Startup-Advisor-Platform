"""
Re-export MentorProfile from the users module.

The model lives in app.users.models alongside User and FounderProfile
(same pattern), but this file exists so `from app.mentor import models`
works in main.py and migrations/env.py — keeping the import style
consistent across all feature modules.
"""

from app.users.models import MentorProfile  # noqa: F401
