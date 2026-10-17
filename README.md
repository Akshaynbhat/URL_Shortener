#URL Shortener

> **CodeAlpha Backend Development Internship Project**  
> Author: **Akshay N Bhat** | Stack: Python 3 · Flask · SQLite · Vanilla JS

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Internship Context](#2-internship-context)
3. [Problem Statement & Objectives](#3-problem-statement--objectives)
4. [Features](#4-features)
5. [Technology Stack](#5-technology-stack)
6. [Architecture Overview](#6-architecture-overview)
7. [Project Structure](#7-project-structure)
8. [Database Schema](#8-database-schema)
9. [Setup — Windows](#9-setup--windows)
10. [Running the Application](#10-running-the-application)
11. [API Documentation](#11-api-documentation)
12. [Testing](#12-testing)
13. [Screenshots](#13-screenshots)
14. [GitHub Upload](#14-github-upload)
15. [Security Considerations](#15-security-considerations)
16. [Known Limitations](#16-known-limitations)
17. [Future Enhancements](#17-future-enhancements)

---

## 1. Project Overview

This project is a fully functional **URL shortener** backend service built with Python and Flask.
It accepts long URLs via a REST API, generates short alphanumeric codes, persists the mappings in SQLite, and redirects visitors from the short URL to the original destination.

A clean, dark-mode frontend is included so the application can be demonstrated through a browser without any external tools.

---

## 2. Internship Context

| Field | Value |
|---|---|
| Internship | CodeAlpha Backend Development Internship |
| Project | URL Shortener |
| Author | Akshay N Bhat |
| Repository | `CodeAlpha_URLShortener` |

---

## 3. Problem Statement & Objectives

**Problem:** Long URLs are hard to share, paste into messages, or remember.

**Solution:** Map each long URL to a short, random 7-character code stored in a database. Any visitor who accesses the short link is immediately redirected to the original URL.

**Objectives:**

- Implement a REST API in Flask with correct HTTP status codes.
- Persist data in SQLite using only Python's built-in `sqlite3` module.
- Validate all user input before touching the database.
- Serve a professional frontend that communicates with the API via `fetch()`.
- Write an automated test suite using `pytest`.
- Follow secure coding practices: parameterised SQL, no stack trace leakage, safe DOM manipulation.

---

## 4. Features

| Feature | Details |
|---|---|
| URL Shortening | `POST /api/shorten` — generates a unique 7-character code |
| Redirect | `GET /<code>` — 302 redirect to original URL |
| List URLs | `GET /api/urls` — returns all saved mappings |
| Health Check | `GET /api/health` — confirms server and database are reachable |
| Frontend | Responsive dark-mode UI with copy-to-clipboard |
| Validation | Rejects invalid schemes, missing fields, whitespace, long URLs, non-strings |
| Error handling | All errors return structured JSON; no stack traces exposed |
| Automated tests | 35+ pytest tests, all isolated with in-memory SQLite |

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web framework | Flask 3.0 |
| Database | SQLite (via built-in `sqlite3`) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Testing | pytest, pytest-flask |
| Version control | Git / GitHub |
| Dev environment | Windows + Visual Studio Code |

---

## 6. Architecture Overview

```
Browser
   │  GET /              → renders index.html
   │  POST /api/shorten  → returns { short_url, ... }
   │  GET /<code>        → 302 redirect
   ▼
Flask app (app.py → url_shortener/__init__.py)
   │
   ├── routes.py       ← HTTP layer: parses requests, returns responses
   ├── services.py     ← Business logic: code generation, collision retry
   ├── validators.py   ← Input validation (URL rules)
   └── database.py     ← All SQLite interaction (parameterised queries)
                              │
                        instance/urls.db  (SQLite file, git-ignored)
```

**Why this separation?**
Each module has one responsibility. Routes handle HTTP. Services handle logic. The database module handles persistence. Validators handle input rules. This makes it easy to test each piece in isolation and to change one layer without breaking others.

---

## 7. Project Structure

```
CodeAlpha_URLShortener/
├── app.py                  # Entry point
├── config.py               # Configuration classes
├── requirements.txt        # Python dependencies
├── pytest.ini              # pytest configuration
├── .gitignore
├── LICENSE
├── README.md
├── instance/
│   └── .gitkeep            # Placeholder (urls.db is git-ignored)
├── url_shortener/
│   ├── __init__.py         # Application factory (create_app)
│   ├── database.py         # SQLite layer
│   ├── services.py         # Short-code generation
│   ├── validators.py       # URL validation
│   ├── routes.py           # All Flask endpoints
│   ├── templates/
│   │   └── index.html      # Single-page frontend
│   └── static/
│       ├── css/style.css
│       └── js/app.js
└── tests/
    ├── conftest.py          # Fixtures (test app + client)
    ├── test_health.py
    ├── test_shorten.py
    ├── test_redirect.py
    └── test_validation.py
```

---

## 8. Database Schema

**Table: `urls`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Row identifier |
| `short_code` | TEXT | NOT NULL, UNIQUE | 7-character random code |
| `original_url` | TEXT | NOT NULL | The original long URL |
| `created_at` | TIMESTAMP | DEFAULT datetime('now') | Creation timestamp |

An index on `short_code` is created automatically (the UNIQUE constraint implies an index; an explicit index is also added for clarity).

The database file lives at `instance/urls.db` and is created automatically on first run. It is excluded from Git.

---

## 9. Setup — Windows

### Prerequisites

- Python 3.11 or later: https://www.python.org/downloads/
- Git: https://git-scm.com/download/win

Verify both are installed:

```powershell
python --version
git --version
```

### 1. Clone or navigate to the project

```powershell
cd C:\URL_shortener
```

### 2. Create a virtual environment

```powershell
# PowerShell
python -m venv .venv

# Command Prompt
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
# PowerShell
.venv\Scripts\Activate.ps1

# Command Prompt
.venv\Scripts\activate.bat
```

You should see `(.venv)` at the start of your prompt.

> **If PowerShell blocks script execution**, run this first (once):
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

---

## 10. Running the Application

```powershell
python app.py
```

Expected output:

```
Initialising database at: C:\URL_shortener\instance\urls.db
Database ready.
 * Running on http://127.0.0.1:5000
```

Open your browser and go to: **http://127.0.0.1:5000**

To stop the server press **Ctrl + C**.

### Configuration via environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_PATH` | `instance/urls.db` | Path to the SQLite database |
| `SECRET_KEY` | `dev-secret-...` | Flask session key — change in production |
| `FLASK_DEBUG` | `false` | Set to `true` only for local dev |

---

## 11. API Documentation

### POST /api/shorten

Create a short URL.

**Request**
```json
POST /api/shorten
Content-Type: application/json

{
  "url": "https://www.example.com/very/long/path?query=value"
}
```

**Success — 201 Created**
```json
{
  "original_url": "https://www.example.com/very/long/path?query=value",
  "short_code": "aB3xYz9",
  "short_url": "http://127.0.0.1:5000/aB3xYz9",
  "created_at": "2024-10-15 12:00:00"
}
```

**Error — 400 Bad Request**
```json
{ "error": "Unsupported URL scheme 'ftp'. Only http and https are allowed." }
```

---

### GET /\<short_code\>

Redirect to the original URL.

| Scenario | Status | Response |
|---|---|---|
| Valid code | 302 | `Location: <original_url>` |
| Unknown code | 404 | `{ "error": "Short code '...' not found." }` |
| Invalid format | 404 | `{ "error": "Invalid short code: '...'." }` |

**PowerShell test:**
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:5000/aB3xYz9" -MaximumRedirection 0
```

---

### GET /api/urls

Return all stored URL mappings.

**Response — 200 OK**
```json
[
  {
    "short_code": "aB3xYz9",
    "original_url": "https://www.example.com/very/long/path",
    "created_at": "2024-10-15 12:00:00",
    "short_url": "http://127.0.0.1:5000/aB3xYz9"
  }
]
```

> ⚠️ This endpoint is intended for **local demonstration** only.
> In production it must be protected with authentication.

---

### GET /api/health

Check application and database status.

**Healthy — 200 OK**
```json
{ "status": "ok", "database": "reachable" }
```

**Degraded — 503 Service Unavailable**
```json
{ "status": "degraded", "database": "unreachable" }
```

---

### HTTP Status Code Reference

| Code | Meaning |
|---|---|
| 200 | Request succeeded |
| 201 | Short URL created successfully |
| 302 | Redirect to original URL |
| 400 | Bad request (invalid input) |
| 404 | Short code not found |
| 405 | Method not allowed |
| 500 | Internal server error |
| 503 | Service degraded (DB unreachable) |

---

## 12. Testing

### Run all tests

```powershell
python -m pytest -v
```

### Run a specific file

```powershell
python -m pytest tests/test_shorten.py -v
```

### Test coverage at a glance

| File | Coverage area |
|---|---|
| `test_health.py` | Health endpoint, DB failure simulation |
| `test_shorten.py` | Successful shortening, DB persistence, distinct codes |
| `test_redirect.py` | Redirect, 404s, malformed codes, security |
| `test_validation.py` | All invalid input types, collision simulation, list endpoint, homepage |

Tests use an **in-memory SQLite database** — they never touch `instance/urls.db`.

---

## 13. Screenshots

> **Manual step required:** Run the application and replace the placeholders below with actual screenshots.

| Screenshot | Description |
|---|---|
| `screenshots/01_homepage.png` | Homepage with the URL input form |
| `screenshots/02_shortened.png` | Success state showing the short URL |
| `screenshots/03_redirect.png` | Browser following a short URL redirect |
| `screenshots/04_api_shorten.png` | `POST /api/shorten` response in Postman or curl |
| `screenshots/05_api_urls.png` | `GET /api/urls` response |
| `screenshots/06_api_health.png` | `GET /api/health` response |
| `screenshots/07_tests_passing.png` | Terminal showing all pytest tests passing |
| `screenshots/08_database.png` | DB Browser for SQLite showing the `urls` table |

---


## 14. Security Considerations

| Concern | How it is addressed |
|---|---|
| SQL injection | All queries use parameterised `?` placeholders |
| XSS | Frontend sets values via `textContent`/`href`, never `innerHTML` |
| Open redirect | Redirect destination always comes from DB, never from user query params |
| Stack trace leakage | Exceptions are logged server-side; generic messages returned to clients |
| Debug mode | `FLASK_DEBUG=true` is off by default; must be set explicitly |
| Secrets in code | `SECRET_KEY` has a placeholder default; override via env var before deployment |
| SSRF | The backend never fetches URLs on behalf of users |
| Path traversal | Short codes are validated against `[A-Za-z0-9_-]+` before any DB query |

**URL reachability is not validated by design.** Checking whether a URL is reachable would require the server to make outbound HTTP requests, which introduces latency, SSRF risk, and external dependencies. The validator only checks syntax and scheme.

---

## 15. Known Limitations

- **No authentication:** The `/api/urls` endpoint is unauthenticated. Suitable for local demos only.
- **No click analytics:** Visit counts are not tracked.
- **No expiry:** Short URLs do not expire.
- **Local only:** Flask's built-in server is not suitable for internet-facing deployment.
- **No rate limiting:** A production deployment would need per-IP rate limiting.
- **URL reachability:** The validator checks syntax, not whether the destination is live.

---

## 16. Future Enhancements

- Custom short codes chosen by the user
- Click-count analytics per short URL
- URL expiry (TTL)
- Admin dashboard with authentication
- QR code generation
- Rate limiting with Flask-Limiter
- Deployment with Gunicorn + Nginx on a cloud VM
- Swap SQLite for PostgreSQL for multi-user production use
