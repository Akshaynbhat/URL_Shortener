"""
config.py — Application configuration for CodeAlpha URL Shortener.

Settings are loaded from environment variables where available,
falling back to safe local defaults for development.

Security note: Never enable DEBUG=True on a public-facing server.
Flask's development server is not designed for production use and
must not be exposed to the internet.
"""

import os


class Config:
    """Base configuration shared by all environments."""

    # Flask secret key — used for session signing.
    # Override via SECRET_KEY environment variable before deploying.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    # Absolute path to the SQLite database file.
    # Stored in the instance/ folder so it is outside the package and
    # easy to exclude from Git.
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH: str = os.environ.get(
        "DATABASE_PATH",
        os.path.join(BASE_DIR, "instance", "urls.db"),
    )

    # Short-code generation settings.
    SHORT_CODE_LENGTH: int = 7          # Characters in each generated code.
    SHORT_CODE_MAX_RETRIES: int = 5     # Max collision retries before giving up.

    # Maximum URL length accepted (characters).  Prevents extremely long inputs.
    MAX_URL_LENGTH: int = 2048

    # Debug mode.  Must be False (or absent) in production.
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"


class TestingConfig(Config):
    """Configuration used exclusively by the automated test suite."""

    TESTING: bool = True
    DEBUG: bool = True

    # Tests get their own in-memory database so they never touch the
    # developer's real data.
    DATABASE_PATH: str = ":memory:"
