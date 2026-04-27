from flask import Flask

from .auth_utils import load_logged_in_user
from .config import Config
from .context import inject_current_user
from .csrf import validate_csrf_for_mutations
from .extensions import db


def create_app(config_object=Config) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_object)

    db.init_app(app)

    # Import models before database initialization so SQLAlchemy knows all tables.
    from . import models  # noqa: F401
    from .blueprints import (
        attachments_bp,
        auth_bp,
        backup_bp,
        main_bp,
        projects_bp,
        tags_bp,
        tasks_bp,
    )

    app.before_request(load_logged_in_user)
    app.before_request(validate_csrf_for_mutations)
    app.context_processor(inject_current_user)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(attachments_bp)
    app.register_blueprint(backup_bp)

    return app
