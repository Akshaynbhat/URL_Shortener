"""
tests/conftest.py

Shared pytest fixtures for the URL Shortener test suite.

Key design decisions
--------------------
* Each test gets its own Flask application instance.
* We use SQLite named in-memory databases (file:testdb_<id>?mode=memory&cache=shared)
  rather than the plain ':memory:' path.  Plain ':memory:' creates a brand-new
  empty database for every sqlite3.connect() call, so init_db and the actual
  queries would see different tables.  Named in-memory databases share the same
  in-memory space for all connections that use the same name, and our
  database.py module caches a single connection per unique path.
* Each test gets a unique name (keyed by its node ID hash) so databases are
  fully isolated between tests.
* The `client` fixture provides a Flask test client that sends HTTP requests
  without starting a real network server.
"""

import hashlib
import pytest

from url_shortener import create_app
from url_shortener.database import release_memory_connection


def _make_test_config(test_id: str):
    """Return a fresh config object with a unique in-memory database path."""
    from config import Config

    # Create a unique but deterministic db name from the test node id.
    short = hashlib.md5(test_id.encode()).hexdigest()[:8]
    db_uri = f"file:testdb_{short}?mode=memory&cache=shared"

    class _TestConfig(Config):
        TESTING = True
        DEBUG = True
        DATABASE_PATH = db_uri

    return _TestConfig


@pytest.fixture(scope="function")
def app(request):
    """
    Create a fresh Flask application instance with an isolated in-memory
    database for each test function.
    """
    cfg = _make_test_config(request.node.nodeid)
    application = create_app(cfg)

    yield application

    # Teardown: remove the shared connection for this test's DB so the
    # next test starts fresh and the connection is properly closed.
    release_memory_connection(application.config["DATABASE_PATH"])


@pytest.fixture(scope="function")
def client(app):
    """
    Provide a Flask test client bound to the isolated test application.
    Use this fixture in every test that sends HTTP requests.
    """
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture(scope="function")
def app_context(app):
    """
    Push an application context for tests that need to call functions that
    use current_app or the database directly (not through HTTP).
    """
    with app.app_context():
        yield app
