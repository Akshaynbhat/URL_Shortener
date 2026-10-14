"""
url_shortener/database.py

All database interaction lives here.  The rest of the application
never imports sqlite3 directly — it calls the functions in this module.

Design decisions
----------------
* We use Python's built-in sqlite3 so there are no ORM dependencies.
* In-memory databases (:memory:) are used exclusively by tests.  Because
  each sqlite3.connect(":memory:") call creates a NEW, EMPTY database, we
  store a shared connection when the path is :memory: so that init_db and
  subsequent queries all see the same tables.
* For real file-based databases each function opens, uses, and CLOSES its
  own connection — ensuring connections are not leaked.
* All SQL uses parameterised queries — never string formatting — to prevent
  SQL injection.
* WAL journal mode and foreign_keys = ON are set for every connection.
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS urls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code  TEXT    NOT NULL UNIQUE,
    original_url TEXT   NOT NULL,
    created_at  TIMESTAMP DEFAULT (datetime('now'))
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls (short_code);
"""

# --------------------------------------------------------------------------- #
# In-memory connection sharing
# --------------------------------------------------------------------------- #
# sqlite3.connect(":memory:") returns a fresh, empty database every time.
# For tests each app instance uses a unique named in-memory URI such as
#   "file:testdb_<id>?mode=memory&cache=shared"
# so that init_db and all subsequent queries within the same test reuse
# the same connection and therefore see the same tables.
# We key the shared connection by the full db_path string.
_MEMORY_CONNECTIONS: dict = {}


def _is_memory_path(db_path: str) -> bool:
    """Return True if this is a path that requires a shared (in-memory) connection."""
    return db_path == ":memory:" or db_path.startswith("file:") and "mode=memory" in db_path


def _get_connection(db_path: str) -> sqlite3.Connection:
    """
    Return a configured SQLite connection.

    For in-memory URIs a shared connection is returned (and stored) so
    that all queries within the same app instance see the same tables.

    For file paths a new connection is opened; callers must close it via
    _close() to avoid ResourceWarning on Python 3.12+.
    """
    if _is_memory_path(db_path):
        if db_path not in _MEMORY_CONNECTIONS:
            use_uri = db_path.startswith("file:")
            conn = sqlite3.connect(db_path, check_same_thread=False, uri=use_uri)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _MEMORY_CONNECTIONS[db_path] = conn
        return _MEMORY_CONNECTIONS[db_path]

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _close(conn: sqlite3.Connection, db_path: str) -> None:
    """Close a connection only if it is NOT a shared in-memory connection."""
    if not _is_memory_path(db_path):
        conn.close()


def release_memory_connection(db_path: str) -> None:
    """
    Explicitly close and remove the shared in-memory connection.

    Call this in test teardown (if needed) to ensure a fresh database for
    the next test run.  In practice the conftest fixture creates a brand-new
    app instance per test, so a new key is used automatically.
    """
    conn = _MEMORY_CONNECTIONS.pop(db_path, None)
    if conn is not None:
        conn.close()


# --------------------------------------------------------------------------- #
# Initialisation
# --------------------------------------------------------------------------- #

def init_db(app) -> None:
    """
    Create the database tables if they do not already exist.

    Called once at application startup inside an app context.
    """
    db_path: str = app.config["DATABASE_PATH"]
    logger.info("Initialising database at: %s", db_path)

    try:
        conn = _get_connection(db_path)
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(_CREATE_INDEX_SQL)
        conn.commit()
        _close(conn, db_path)
        logger.info("Database ready.")
    except sqlite3.Error as exc:
        logger.error("Failed to initialise database: %s", exc)
        raise


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #

def insert_url(db_path: str, short_code: str, original_url: str) -> Optional[dict]:
    """
    Insert a new short-code → URL mapping and return the inserted row.

    Returns None on a UNIQUE constraint violation (collision).
    Raises sqlite3.Error for any other database error.
    """
    sql = "INSERT INTO urls (short_code, original_url) VALUES (?, ?)"
    try:
        conn = _get_connection(db_path)
        conn.execute(sql, (short_code, original_url))
        conn.commit()
        _close(conn, db_path)
        return get_url_by_code(db_path, short_code)
    except sqlite3.IntegrityError:
        logger.warning("Short-code collision detected: %s", short_code)
        return None
    except sqlite3.Error as exc:
        logger.error("Database error during insert: %s", exc)
        raise


def get_url_by_code(db_path: str, short_code: str) -> Optional[dict]:
    """Return the URL mapping row for the given short code, or None."""
    sql = "SELECT id, short_code, original_url, created_at FROM urls WHERE short_code = ?"
    try:
        conn = _get_connection(db_path)
        row = conn.execute(sql, (short_code,)).fetchone()
        _close(conn, db_path)
        return dict(row) if row else None
    except sqlite3.Error as exc:
        logger.error("Database error during lookup: %s", exc)
        raise


def get_all_urls(db_path: str) -> list:
    """Return all stored URL mappings ordered by creation date (newest first)."""
    sql = "SELECT id, short_code, original_url, created_at FROM urls ORDER BY created_at DESC"
    try:
        conn = _get_connection(db_path)
        rows = conn.execute(sql).fetchall()
        _close(conn, db_path)
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Database error during list: %s", exc)
        raise


def health_check(db_path: str) -> bool:
    """
    Verify the database is reachable by executing a trivial query.

    Returns True if healthy, False otherwise.
    """
    try:
        conn = _get_connection(db_path)
        conn.execute("SELECT 1").fetchone()
        _close(conn, db_path)
        return True
    except sqlite3.Error as exc:
        logger.error("Database health check failed: %s", exc)
        return False
