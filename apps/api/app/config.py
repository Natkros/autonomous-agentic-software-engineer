"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production"


class InsecureProductionConfigError(RuntimeError):
    """Raised at startup, never silently ignored — a production deployment
    running with a well-known default secret is a real vulnerability, not
    a warning to log and move past.
    """


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ForgeAI API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://forgeai:forgeai@localhost:5432/forgeai"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:3000"]

    def validate_for_startup(self) -> None:
        """Fail loudly at process startup rather than quietly serving
        production traffic with a secret every clone of this repository
        already knows. Never called by the test suite (`environment` is
        forced to "test" there — see `tests/conftest.py`), so this can
        never fail a test run.
        """
        if self.environment == "production" and self.jwt_secret == DEFAULT_JWT_SECRET:
            raise InsecureProductionConfigError(
                "JWT_SECRET is still the default placeholder value while ENVIRONMENT=production. "
                "Set a real, random JWT_SECRET before serving production traffic."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
