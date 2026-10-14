"""
url_shortener/validators.py

URL validation logic.  Keeping validation in its own module makes it
easy to test independently and to tighten rules without touching routes.

What this validator checks
--------------------------
* The value is a non-empty string.
* The string is not longer than MAX_URL_LENGTH characters.
* The string contains no whitespace (spaces, tabs, newlines).
* The URL can be parsed by urllib.parse.urlparse.
* The scheme is http or https (ftp, javascript, data, etc. are rejected).
* A hostname is present.

What this validator does NOT check
-----------------------------------
* Whether the server at that hostname is actually reachable.
* Whether the resource at the URL returns a 200 OK.
* Certificate validity.

This is intentional: validating reachability would require the backend to
make outbound HTTP requests, which introduces latency, SSRF risk, and
external dependencies.  The README explains this limitation.
"""

import re
from urllib.parse import urlparse

# Only these URI schemes are accepted.
ALLOWED_SCHEMES = {"http", "https"}

# Maximum URL length (characters).  This default is overridden by config.
DEFAULT_MAX_URL_LENGTH = 2048

# Allowed characters in a short code (URL-safe alphanumeric).
# We also compile a pattern to quickly validate codes from the redirect route.
_SHORT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_url(value, max_length: int = DEFAULT_MAX_URL_LENGTH) -> tuple[bool, str]:
    """
    Validate that *value* is an acceptable URL to shorten.

    Parameters
    ----------
    value : any
        The value supplied by the caller (may be any type).
    max_length : int
        Maximum number of characters allowed.

    Returns
    -------
    (is_valid : bool, error_message : str)
        If is_valid is True, error_message is an empty string.
        If is_valid is False, error_message describes the problem.
    """

    # 1. Must be a string.
    if not isinstance(value, str):
        return False, "The 'url' field must be a string."

    # 2. Must not be empty.
    url = value.strip()
    if not url:
        return False, "A URL is required and must not be empty."

    # 3. We do NOT silently strip — if the user supplied whitespace inside
    #    or around the URL, we reject it.  Leading/trailing spaces are a
    #    common mistake but we return the original value in error responses,
    #    which helps the caller diagnose the problem.
    if value != value.strip() or " " in value or "\t" in value or "\n" in value:
        return False, "The URL must not contain whitespace."

    # 4. Length check.
    if len(value) > max_length:
        return False, f"The URL must not exceed {max_length} characters."

    # 5. Parse the URL.
    try:
        parsed = urlparse(value)
    except ValueError:
        return False, "The URL could not be parsed."

    # 6. Scheme must be http or https.
    if parsed.scheme not in ALLOWED_SCHEMES:
        if parsed.scheme == "":
            return False, "The URL must include a scheme (http:// or https://)."
        return (
            False,
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )

    # 7. A hostname must be present.
    if not parsed.hostname:
        return False, "The URL must include a valid hostname."

    return True, ""


def validate_short_code(code: str) -> bool:
    """
    Return True if *code* consists only of URL-safe alphanumeric characters,
    hyphens, and underscores.

    This prevents the redirect route from being probed with path-traversal
    sequences such as '../etc/passwd'.

    Parameters
    ----------
    code : str

    Returns
    -------
    bool
    """
    if not code or not isinstance(code, str):
        return False
    return bool(_SHORT_CODE_PATTERN.match(code))
