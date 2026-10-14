"""
app.py — Entry point for the CodeAlpha URL Shortener.

Run with:
    python app.py

The application is configured through config.py and environment variables.
Flask's built-in development server is used here for local development only.

Production warning
------------------
Flask's development server (Werkzeug) is NOT suitable for internet-facing
deployment.  For production, use a WSGI server such as Gunicorn or Waitress
behind a reverse proxy (e.g. Nginx).  That deployment scenario is beyond the
scope of this internship project.
"""

from url_shortener import create_app
from config import Config

app = create_app(Config)

if __name__ == "__main__":
    # debug=False unless FLASK_DEBUG=true is set in the environment.
    # host="127.0.0.1" binds only to localhost — never exposes the dev
    # server to other machines on the network.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=Config.DEBUG,
    )
