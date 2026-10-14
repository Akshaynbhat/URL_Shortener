"""
tests/test_validation.py

Tests for URL validation rules applied by POST /api/shorten.

Each test focuses on one invalid input category and verifies that:
  1. The response status code is 400 Bad Request.
  2. The response body is JSON with an "error" field.

Tests also cover:
  - The homepage (GET /)
  - The URL list endpoint (GET /api/urls)
  - Database isolation between tests
  - Short-code collision simulation
"""

import json
import unittest.mock as mock


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #

def post(client, payload, content_type="application/json"):
    return client.post(
        "/api/shorten",
        data=json.dumps(payload),
        content_type=content_type,
    )


def assert_bad_request(response):
    """Assert the response is 400 with a JSON error field."""
    assert response.status_code == 400, (
        f"Expected 400 but got {response.status_code}: {response.data}"
    )
    data = response.get_json()
    assert data is not None, "Response is not valid JSON"
    assert "error" in data, f"Response has no 'error' key: {data}"


# --------------------------------------------------------------------------- #
# Homepage
# --------------------------------------------------------------------------- #

class TestHomepage:
    def test_homepage_returns_200(self, client):
        """GET / must return HTTP 200 and serve the HTML page."""
        response = client.get("/")
        assert response.status_code == 200

    def test_homepage_is_html(self, client):
        """GET / must return an HTML content type."""
        response = client.get("/")
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data


# --------------------------------------------------------------------------- #
# Missing / empty URL field
# --------------------------------------------------------------------------- #

class TestMissingUrl:
    def test_missing_url_field_returns_400(self, client):
        """Omitting the 'url' key entirely must return 400."""
        response = post(client, {})
        assert_bad_request(response)

    def test_empty_string_returns_400(self, client):
        """An empty string URL must be rejected."""
        response = post(client, {"url": ""})
        assert_bad_request(response)

    def test_whitespace_only_returns_400(self, client):
        """A whitespace-only string must be rejected."""
        response = post(client, {"url": "   "})
        assert_bad_request(response)


# --------------------------------------------------------------------------- #
# Non-string types
# --------------------------------------------------------------------------- #

class TestNonStringUrl:
    def test_integer_url_returns_400(self, client):
        response = post(client, {"url": 12345})
        assert_bad_request(response)

    def test_null_url_returns_400(self, client):
        response = post(client, {"url": None})
        assert_bad_request(response)

    def test_list_url_returns_400(self, client):
        response = post(client, {"url": ["https://example.com"]})
        assert_bad_request(response)

    def test_object_url_returns_400(self, client):
        response = post(client, {"url": {"href": "https://example.com"}})
        assert_bad_request(response)

    def test_bool_url_returns_400(self, client):
        response = post(client, {"url": True})
        assert_bad_request(response)


# --------------------------------------------------------------------------- #
# Unsupported or malformed URLs
# --------------------------------------------------------------------------- #

class TestUnsupportedSchemes:
    def test_ftp_scheme_returns_400(self, client):
        response = post(client, {"url": "ftp://files.example.com/file.zip"})
        assert_bad_request(response)

    def test_javascript_scheme_returns_400(self, client):
        response = post(client, {"url": "javascript:alert('xss')"})
        assert_bad_request(response)

    def test_data_scheme_returns_400(self, client):
        response = post(client, {"url": "data:text/html,<h1>Hello</h1>"})
        assert_bad_request(response)

    def test_no_scheme_returns_400(self, client):
        response = post(client, {"url": "www.example.com/no-scheme"})
        assert_bad_request(response)

    def test_scheme_only_returns_400(self, client):
        response = post(client, {"url": "https://"})
        assert_bad_request(response)


class TestMalformedUrls:
    def test_url_with_spaces_returns_400(self, client):
        response = post(client, {"url": "https://www.example.com/path with spaces"})
        assert_bad_request(response)

    def test_url_with_leading_space_returns_400(self, client):
        response = post(client, {"url": " https://www.example.com"})
        assert_bad_request(response)

    def test_url_with_trailing_space_returns_400(self, client):
        response = post(client, {"url": "https://www.example.com "})
        assert_bad_request(response)

    def test_very_long_url_returns_400(self, client):
        """A URL exceeding MAX_URL_LENGTH must be rejected."""
        long_url = "https://www.example.com/" + "a" * 3000
        response = post(client, {"url": long_url})
        assert_bad_request(response)


# --------------------------------------------------------------------------- #
# Invalid JSON body
# --------------------------------------------------------------------------- #

class TestInvalidJson:
    def test_plain_text_body_returns_400(self, client):
        """Sending a plain-text body with JSON content-type must return 400."""
        response = client.post(
            "/api/shorten",
            data="this is not json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_wrong_content_type_returns_400(self, client):
        """Sending form data instead of JSON must return 400."""
        response = client.post(
            "/api/shorten",
            data={"url": "https://www.example.com"},
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 400

    def test_empty_body_returns_400(self, client):
        """An empty request body must return 400."""
        response = client.post(
            "/api/shorten",
            data="",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_json_array_body_returns_400(self, client):
        """A JSON array (not an object) must return 400."""
        response = client.post(
            "/api/shorten",
            data=json.dumps(["https://example.com"]),
            content_type="application/json",
        )
        assert response.status_code == 400


# --------------------------------------------------------------------------- #
# URL list endpoint
# --------------------------------------------------------------------------- #

class TestUrlList:
    def test_url_list_returns_200(self, client):
        response = client.get("/api/urls")
        assert response.status_code == 200

    def test_url_list_returns_json_array(self, client):
        response = client.get("/api/urls")
        data = response.get_json()
        assert isinstance(data, list)

    def test_url_list_empty_on_fresh_db(self, client):
        """With a fresh in-memory database there should be no entries."""
        response = client.get("/api/urls")
        assert response.get_json() == []

    def test_url_list_contains_expected_fields(self, client):
        """Each list item must have the required fields."""
        post(client, {"url": "https://www.example.com/listed"})
        response = client.get("/api/urls")
        items = response.get_json()
        assert len(items) >= 1
        item = items[0]
        for field in ("short_code", "original_url", "created_at", "short_url"):
            assert field in item, f"Missing field: {field}"

    def test_url_list_isolation(self, client, app):
        """
        Each test's database is independent.  A URL added in one test must
        not appear in a different test's database.
        """
        # This test runs against its own fresh in-memory database.
        response = client.get("/api/urls")
        assert response.get_json() == [], "Database is not isolated between tests"


# --------------------------------------------------------------------------- #
# Collision simulation
# --------------------------------------------------------------------------- #

class TestCollisionHandling:
    def test_collision_is_retried_successfully(self, client):
        """
        Simulate a short-code collision by patching _generate_code to return a
        fixed value on the first call, then a unique value on subsequent calls.
        The service must retry and succeed.
        """
        call_count = {"n": 0}

        def mock_generate(length):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "AAAAAA1"   # First call: store this code normally
            if call_count["n"] == 2:
                return "AAAAAA1"   # Second call: same code → collision
            return "NEWCODE"       # Third call: new unique code

        with mock.patch("url_shortener.services._generate_code", side_effect=mock_generate):
            # First request stores "AAAAAA1"
            r1 = post(client, {"url": "https://www.first.com"})
            assert r1.status_code == 201
            assert r1.get_json()["short_code"] == "AAAAAA1"

            # Second request hits a collision on "AAAAAA1" then succeeds with "NEWCODE"
            r2 = post(client, {"url": "https://www.second.com"})
            assert r2.status_code == 201
            assert r2.get_json()["short_code"] == "NEWCODE"
