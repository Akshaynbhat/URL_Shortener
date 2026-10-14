"""
url_shortener/routes.py

All Flask route handlers are defined here and registered through a Blueprint.

Endpoints
---------
GET  /                  — Homepage (HTML)
POST /api/shorten       — Create a short URL
GET  /api/urls          — List all short URLs
GET  /api/health        — Application / DB health check
GET  /<short_code>      — Redirect to original URL

Security notes
--------------
* We never reflect user-supplied values into error messages in a way that
  could cause XSS; Flask's jsonify escapes values.
* The redirect destination is always the value stored in the database —
  never a user-controlled query parameter — so open-redirect attacks are
  not possible through this endpoint.
* Stack traces are never exposed to API clients.  Internal errors are logged
  server-side and a generic message is returned to the caller.
"""

import logging
import sqlite3

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .database import get_all_urls, health_check
from .services import lookup_url, shorten_url
from .validators import validate_short_code, validate_url

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


# --------------------------------------------------------------------------- #
# Homepage
# --------------------------------------------------------------------------- #

@bp.route("/")
def index():
    """Serve the single-page HTML frontend."""
    return render_template("index.html")


# --------------------------------------------------------------------------- #
# Health check
# --------------------------------------------------------------------------- #

@bp.route("/api/health")
def health():
    """
    Return application status and database reachability.

    200 — Everything is healthy.
    503 — Application is running but database is unreachable.
    """
    db_path: str = current_app.config["DATABASE_PATH"]
    db_ok = health_check(db_path)

    payload = {
        "status": "ok" if db_ok else "degraded",
        "database": "reachable" if db_ok else "unreachable",
    }

    status_code = 200 if db_ok else 503
    return jsonify(payload), status_code


# --------------------------------------------------------------------------- #
# Shorten a URL
# --------------------------------------------------------------------------- #

@bp.route("/api/shorten", methods=["POST"])
def shorten():
    """
    Accept a long URL and return a short URL.

    Request body (JSON)
    -------------------
    { "url": "https://www.example.com/some/long/path" }

    Responses
    ---------
    201 Created       — Successful shortening.
    400 Bad Request   — Missing field, invalid URL, or bad JSON.
    500 Internal      — Unexpected database or server error.
    """
    # --- Parse JSON body --------------------------------------------------- #
    if not request.is_json:
        return (
            jsonify({"error": "Request must have Content-Type: application/json."}),
            400,
        )

    try:
        data = request.get_json(force=False, silent=False)
    except Exception:
        return jsonify({"error": "Request body contains invalid JSON."}), 400

    if data is None:
        return jsonify({"error": "Request body contains invalid JSON."}), 400

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    # --- Validate the URL -------------------------------------------------- #
    raw_url = data.get("url")

    max_length: int = current_app.config.get("MAX_URL_LENGTH", 2048)
    is_valid, error_msg = validate_url(raw_url, max_length=max_length)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # --- Generate and store the short code --------------------------------- #
    try:
        row = shorten_url(current_app._get_current_object(), raw_url)
    except RuntimeError as exc:
        # All collision retries exhausted — extremely unlikely.
        logger.error("shorten_url failed: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except sqlite3.Error as exc:
        logger.error("Database error in /api/shorten: %s", exc)
        return jsonify({"error": "A database error occurred. Please try again."}), 500
    except Exception as exc:
        logger.error("Unexpected error in /api/shorten: %s", exc)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

    # Build the short URL using the request's host so the URL is correct
    # regardless of which host the server is running on.
    short_url = request.host_url.rstrip("/") + "/" + row["short_code"]

    response_data = {
        "original_url": row["original_url"],
        "short_code": row["short_code"],
        "short_url": short_url,
        "created_at": row["created_at"],
    }

    return jsonify(response_data), 201


# --------------------------------------------------------------------------- #
# List all URLs
# --------------------------------------------------------------------------- #

@bp.route("/api/urls")
def list_urls():
    """
    Return all stored URL mappings as a JSON array.

    ⚠️  Development / demo endpoint only.  This endpoint is not
    authenticated and must not be exposed publicly without access controls.

    200 — Array of URL objects (may be empty).
    500 — Database error.
    """
    db_path: str = current_app.config["DATABASE_PATH"]

    try:
        rows = get_all_urls(db_path)
    except sqlite3.Error as exc:
        logger.error("Database error in /api/urls: %s", exc)
        return jsonify({"error": "A database error occurred."}), 500

    host = request.host_url.rstrip("/")
    result = [
        {
            "short_code": r["short_code"],
            "original_url": r["original_url"],
            "created_at": r["created_at"],
            "short_url": f"{host}/{r['short_code']}",
        }
        for r in rows
    ]

    return jsonify(result), 200


# --------------------------------------------------------------------------- #
# Redirect
# --------------------------------------------------------------------------- #

@bp.route("/<short_code>")
def redirect_to_url(short_code: str):
    """
    Redirect a short code to its stored original URL.

    Security: the redirect destination is always fetched from the database.
    User-supplied query parameters are never used as redirect targets.

    200  — Not used (redirect responses are 302).
    302  — Found; redirect to original URL.
    404  — Short code not found or has invalid characters.
    500  — Database error.
    """
    # Reject codes with unexpected characters before touching the database.
    if not validate_short_code(short_code):
        return jsonify({"error": f"Invalid short code: '{short_code}'."}), 404

    try:
        row = lookup_url(current_app._get_current_object(), short_code)
    except sqlite3.Error as exc:
        logger.error("Database error in redirect for code '%s': %s", short_code, exc)
        return jsonify({"error": "A database error occurred."}), 500

    if row is None:
        return jsonify({"error": f"Short code '{short_code}' not found."}), 404

    # The destination comes from the database — not from any request parameter.
    return redirect(row["original_url"], code=302)


# --------------------------------------------------------------------------- #
# Global error handlers
# --------------------------------------------------------------------------- #

@bp.app_errorhandler(404)
def not_found(error):
    """Return a JSON 404 for API-prefixed paths, HTML otherwise."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    return render_template("index.html"), 404


@bp.app_errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed."}), 405


@bp.app_errorhandler(500)
def internal_error(error):
    logger.error("Unhandled 500 error: %s", error)
    return jsonify({"error": "An internal server error occurred."}), 500
