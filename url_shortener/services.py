"""
url_shortener/services.py

Business logic for generating short codes and persisting URL mappings.

Short-code generation strategy
-------------------------------
We use Python's `secrets` module (backed by the OS CSPRNG) to pick
characters from a 62-character alphabet of uppercase letters, lowercase
letters, and digits.

Why not uuid4?
  UUIDs are 36 characters.  7 random alphanumeric characters give
  62^7 ≈ 3.5 billion unique codes, which is more than adequate for a
  local demonstration.

Why not a hash of the URL?
  Hashing the URL means two requests for the same URL always return the
  same code, which looks nice but complicates the data model.  We deliberately
  generate a fresh code on each request so the tests stay simple and the
  application is easier to understand.

Collision handling
------------------
A UNIQUE constraint on the short_code column prevents duplicates.
insert_url() returns None on a collision.  shorten_url() retries up to
SHORT_CODE_MAX_RETRIES times before raising RuntimeError.  In practice,
with a 62^7 code space the probability of a collision is negligible until
billions of rows exist.
"""

import secrets
import string
import logging
from typing import Optional

from flask import Flask

from .database import insert_url, get_url_by_code

logger = logging.getLogger(__name__)

# Alphabet for short codes.  Only URL-safe characters.
_ALPHABET = string.ascii_letters + string.digits  # A-Z a-z 0-9


def _generate_code(length: int) -> str:
    """
    Return a cryptographically random string of *length* characters chosen
    from _ALPHABET.
    """
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def shorten_url(app: Flask, original_url: str) -> dict:
    """
    Generate a unique short code, persist the mapping, and return the record.

    Parameters
    ----------
    app : Flask
        The running application (used for config values).
    original_url : str
        The validated original URL to shorten.

    Returns
    -------
    dict
        The stored record containing short_code, original_url, created_at.

    Raises
    ------
    RuntimeError
        If a unique code cannot be generated after the maximum number of retries.
    """
    db_path: str = app.config["DATABASE_PATH"]
    code_length: int = app.config["SHORT_CODE_LENGTH"]
    max_retries: int = app.config["SHORT_CODE_MAX_RETRIES"]

    for attempt in range(1, max_retries + 1):
        code = _generate_code(code_length)
        logger.debug("Attempt %d: trying short code '%s'", attempt, code)

        row = insert_url(db_path, code, original_url)

        if row is not None:
            # Successful insert — return the stored record.
            logger.info("Stored short code '%s' for URL: %s", code, original_url)
            return row

        # Collision — try again.
        logger.warning("Collision on attempt %d for code '%s'. Retrying.", attempt, code)

    # Extremely unlikely to reach here.
    logger.error(
        "Could not generate a unique short code after %d attempts.", max_retries
    )
    raise RuntimeError(
        f"Failed to generate a unique short code after {max_retries} attempts. "
        "Please try again."
    )


def lookup_url(app: Flask, short_code: str) -> Optional[dict]:
    """
    Return the URL mapping for *short_code*, or None if it does not exist.

    Parameters
    ----------
    app : Flask
    short_code : str

    Returns
    -------
    dict or None
    """
    db_path: str = app.config["DATABASE_PATH"]
    return get_url_by_code(db_path, short_code)
