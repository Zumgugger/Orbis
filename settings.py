"""
Application settings with validation using pydantic-settings.

Environment variables are automatically loaded and validated at startup.
Missing required settings will raise an error immediately.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required in production:
        - SECRET_KEY: Must be set to a secure random value
        - DATABASE_URL: Database connection string

    Optional:
        - GOOGLE_CLIENT_ID: For OAuth authentication
        - GOOGLE_CLIENT_SECRET: For OAuth authentication
        - DEFAULT_TIMEZONE: User's default timezone (default: Europe/Zurich)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core settings
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for session signing. MUST be changed in production.",
    )
    DATABASE_URL: str = Field(
        default="sqlite:///orbis.db",
        description="Database connection string",
    )
    ORBIS_CONFIG: Literal["development", "production", "test", "testing"] = Field(
        default="development",
        description="Application environment",
    )

    # OAuth settings (optional for dev, required for production OAuth)
    GOOGLE_CLIENT_ID: str | None = Field(
        default=None,
        description="Google OAuth client ID",
    )
    GOOGLE_CLIENT_SECRET: str | None = Field(
        default=None,
        description="Google OAuth client secret",
    )
    GOOGLE_CLIENT_SECRETS_FILE: str | None = Field(
        default=None,
        description="Path to Google OAuth secrets JSON file",
    )

    # Application settings
    DEFAULT_TIMEZONE: str = Field(
        default="Europe/Zurich",
        description="Default timezone for date/time operations",
    )
    DEVELOPMENT_MODE: bool = Field(
        default=False,
        description="Enable development-only features like dev login",
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=10,
        description="Maximum file upload size in megabytes",
    )
    UPLOAD_FOLDER: str = Field(
        default="uploads",
        description="Directory for uploaded files",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Warn if using default secret key in production."""
        # We can't access ORBIS_CONFIG here directly, so just check the value
        if v == "dev-secret-key-change-in-production":
            import os
            import warnings

            env = os.getenv("ORBIS_CONFIG", "development")
            if env == "production":
                raise ValueError(
                    "SECRET_KEY must be set to a secure value in production"
                )
            warnings.warn(
                "Using default SECRET_KEY. Set SECRET_KEY environment variable "
                "in production.",
                stacklevel=2,
            )
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ORBIS_CONFIG == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ORBIS_CONFIG in ("development", "dev")

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.ORBIS_CONFIG in ("test", "testing")

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Settings are loaded once and cached for performance.
    Call get_settings.cache_clear() to reload settings.
    """
    return Settings()


# Convenience function for quick access
def settings() -> Settings:
    """Get application settings."""
    return get_settings()
