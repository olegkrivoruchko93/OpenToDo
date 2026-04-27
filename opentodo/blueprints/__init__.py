from .attachments import bp as attachments_bp
from .auth import bp as auth_bp
from .backup import bp as backup_bp
from .main import bp as main_bp
from .projects import bp as projects_bp
from .tags import bp as tags_bp
from .tasks import bp as tasks_bp


__all__ = [
    "attachments_bp",
    "auth_bp",
    "backup_bp",
    "main_bp",
    "projects_bp",
    "tags_bp",
    "tasks_bp",
]
