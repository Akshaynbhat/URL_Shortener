"""
tests/test_redirect.py

Tests for:
  GET /<short_code>  — redirect endpoint
"""

import json


def shorten(client, url: str) -> str:
    """Helper: shorten a URL and return the generated short code."""
    resp = client.post(
        "/api/shorten",
        data=json.dumps({"url": url}),
        content_type="application/json",
    )
    assert resp.status_code == 201, f"Shortening failed: {resp.get_json()}"
    return resp.get_json()["short_code"]


class TestRedirect:
    """Tests for the redirect route."""

    def test_valid_code_returns_302(self, client):
        """A known short code must return a 302 redirect."""
        code = shorten(client, "https://www.example.com/redirect-test")
        response = client.get(f"/{code}")
        assert response.status_code == 302

    def test_redirect_location_is_original_url(self, client):
        """The Location header must equal the stored original URL."""
        original = "https://www.example.com/specific-destination"
        code = shorten(client, original)
        response = client.get(f"/{code}")
        assert response.headers["Location"] == original

    def test_unknown_code_returns_404(self, client):
        """A code that was never created must return 404."""
        response = client.get("/ZZZZZZZ")
        assert response.status_code == 404

    def test_unknown_code_returns_json_error(self, client):
        """404 response must be a JSON error object."""
        response = client.get("/AAAAAAA")
        data = response.get_json()
        assert data is not None
        assert "error" in data

    def test_malformed_code_with_special_chars_returns_404(self, client):
        """Short codes containing path-traversal or unusual chars must be rejected."""
        # Path traversal attempt
        response = client.get("/../../etc/passwd")
        # Flask may return 404 at routing level; either 400 or 404 is acceptable.
        assert response.status_code in (400, 404)

    def test_malformed_code_with_spaces_returns_404(self, client):
        """A short code containing a space is invalid."""
        # Spaces are percent-encoded in URLs; the encoded form is not alphanumeric.
        response = client.get("/bad%20code")
        assert response.status_code == 404

    def test_redirect_destination_is_from_database(self, client):
        """
        The redirect must go to the stored URL, not any user-supplied parameter.
        Verify by storing URL A, then confirming the redirect goes to A — not
        some attacker-controlled value passed in a query string.
        """
        stored_url = "https://www.legitimate-site.com/"
        code = shorten(client, stored_url)

        # Even if an attacker appends ?url=evil.com the redirect goes to stored_url.
        response = client.get(f"/{code}?url=https://evil.com")
        assert response.headers["Location"] == stored_url

    def test_different_codes_redirect_to_different_urls(self, client):
        """Two different short codes must point to their respective URLs."""
        url_a = "https://www.site-a.com/"
        url_b = "https://www.site-b.com/"
        code_a = shorten(client, url_a)
        code_b = shorten(client, url_b)

        resp_a = client.get(f"/{code_a}")
        resp_b = client.get(f"/{code_b}")

        assert resp_a.headers["Location"] == url_a
        assert resp_b.headers["Location"] == url_b
