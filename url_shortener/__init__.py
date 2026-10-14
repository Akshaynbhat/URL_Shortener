"""
url_shortener/__init__.py

Application factory.  Calling create_app() is the single point of
truth for creating a configured Flask application.  This makes it
easy to create different instances for development, testing, and
production without global state.
"""

import os
from flask import Flask

from .database import init_db
from .routes import bp


def create_app(config_object=None) -> Flask:
    """
    Create and return a configured Flask application instance.

    Parameters
    ----------
    config_object : object or None
        A configuration class (e.g. config.Config or config.TestingConfig).
        If None the default Config class is used.

    Returns
    -------
    Flask
        Fully configured application ready to run or be tested.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ------------------------------------------------------------------ #
    # Load configuration
    # ------------------------------------------------------------------ #
    if config_object is None:
        from config import Config
        config_object = Config

    app.config.from_object(config_object)

    # Ensure the instance folder exists so SQLite can write its file there.
    instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
    os.makedirs(instance_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Initialise the database (creates tables if they do not exist)
    # ------------------------------------------------------------------ #
    with app.app_context():
        init_db(app)

    # ------------------------------------------------------------------ #
    # Register blueprints / routes
    # ------------------------------------------------------------------ #
    app.register_blueprint(bp)

    return app
