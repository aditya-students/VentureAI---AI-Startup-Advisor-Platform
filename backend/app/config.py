"""
Centralized application configuration.

All environment-driven values (DB connection, JWT secrets, cookie flags,
CORS origins) are read once here via pydantic-settings and imported
everywhere else as `settings`. Keeping this in one place avoids scattering
os.environ.get() calls across the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://ventureai_user:ventureai_pass@localhost:5432/ventureai"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-this-to-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Cookies ---
    # False in local dev (http://localhost), MUST be True in production (https only)
    COOKIE_SECURE: bool = False

    # --- CORS ---
    # Comma-separated origins in .env, parsed into a list below
    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500"

    # --- Gemini AI ---
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
