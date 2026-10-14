"""
tests/test_shorten.py

Tests for:
  POST /api/shorten  — URL shortening endpoint
"""

import re
import json


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def post_url(client, url, content_type="application/json"):
    """Submit a URL shortening request and return the response."""
    return client.post(
        "/api/shorten",
        data=json.dumps({"url": url}),
        content_type=content_type,
    )


# --------------------------------------------------------------------------- #
# Successful shortening
# --------------------------------------------------------------------------- #

class TestSuccessfulShortening:
    """A valid URL must be shortened and return HTTP 201."""

    def test_returns_201(self, client):
        response = post_url(client, "https://www.example.com/some/long/path")
        assert response.status_code == 201

    def test_returns_json(self, client):
        response = post_url(client, "https://www.example.com/path")
        data = response.get_json()
        assert data is not None

    def test_response_contains_original_url(self, client):
        original = "https://www.example.com/my-long-url"
        response = post_url(client, original)
        data = response.get_json()
        assert data["original_url"] == original

    def test_response_contains_short_code(self, client):
        response = post_url(client, "https://www.example.com")
        data = response.get_json()
        assert "short_code" in data
        assert isinstance(data["short_code"], str)

    def test_short_code_format(self, client):
        """Short code must contain only alphanumeric characters."""
        response = post_url(client, "https://www.example.com")
        data = response.get_json()
        code = data["short_code"]
        assert re.match(r"^[A-Za-z0-9]+$", code), f"Unexpected short code format: {code}"

    def test_short_code_length(self, client):
        """Default short code length is 7 characters."""
        response = post_url(client, "https://www.example.com")
        data = response.get_json()
        assert len(data["short_code"]) == 7

    def test_response_contains_short_url(self, client):
        response = post_url(client, "https://www.example.com")
        data = response.get_json()
        assert "short_url" in data
        assert data["short_code"] in data["short_url"]

    def test_response_contains_created_at(self, client):
        response = post_url(client, "https://www.example.com")
        data = response.get_json()
        assert "created_at" in data

    def test_two_requests_generate_distinct_codes(self, client):
        """Two shortening requests for the same URL must produce different codes."""
        r1 = post_url(client, "https://www.example.com/same-url")
        r2 = post_url(client, "https://www.example.com/same-url")
        c1 = r1.get_json()["short_code"]
        c2 = r2.get_json()["short_code"]
        assert c1 != c2, "Two requests produced the same short code — generation is not random"

    def test_http_urls_are_accepted(self, client):
        """Plain http:// URLs (not HTTPS) should also be accepted."""
        response = post_url(client, "http://www.example.com/plain-http")
        assert response.status_code == 201

    def test_url_is_stored_verbatim(self, client):
        """The original URL must be stored exactly as supplied."""
        original = "https://www.example.com/path?query=value&another=one"
        response = post_url(client, original)
        data = response.get_json()
        assert data["original_url"] == original


# --------------------------------------------------------------------------- #
# Database persistence
# --------------------------------------------------------------------------- #

class TestDatabasePersistence:
    """The stored short code must be resolvable via the redirect endpoint."""

    def test_stored_code_is_redirectable(self, client):
        """After shortening a URL the redirect endpoint must find it."""
        original = "https://www.google.com"
        shorten_resp = post_url(client, original)
        code = shorten_resp.get_json()["short_code"]

        redirect_resp = client.get(f"/{code}")
        # 302 redirect to the original URL
        assert redirect_resp.status_code == 302
        assert redirect_resp.headers["Location"] == original

    def test_url_list_includes_new_entry(self, client):
        """After shortening, the entry must appear in GET /api/urls."""
        original = "https://www.persisted.com/page"
        shorten_resp = post_url(client, original)
        code = shorten_resp.get_json()["short_code"]

        list_resp = client.get("/api/urls")
        items = list_resp.get_json()
        codes = [item["short_code"] for item in items]
        assert code in codes
