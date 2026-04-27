from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .constants import DEFAULT_PROJECT_ICON, DEFAULT_TASK_PRIORITY
from .extensions import db


task_tag = db.Table(
    "task_tag",
    db.Column("task_id", db.Integer, db.ForeignKey("task.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class User(db.Model):
    """Registered application user with task ownership and Telegram settings."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    telegram_bot_token = db.Column(db.String(255), nullable=True)
    telegram_chat_id = db.Column(db.String(64), nullable=True)
    telegram_username = db.Column(db.String(128), nullable=True)
    telegram_notifications_enabled = db.Column(db.Boolean, default=False, nullable=False)
    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")
    projects = db.relationship("Project", backref="owner", lazy=True, cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and store a new password for the user."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return whether a plain password matches the stored hash."""
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    """User task with optional deadline, project, tags, checklist, and files."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    due_date = db.Column(db.Date, nullable=True)
    due_at = db.Column(db.DateTime, nullable=True)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    telegram_notification_enabled = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.String(16), default=DEFAULT_TASK_PRIORITY, nullable=False)
    recurrence = db.Column(db.String(16), nullable=True)
    recurrence_parent_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=True)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True)
    checklist_items = db.relationship(
        "ChecklistItem",
        backref="task",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ChecklistItem.position.asc()",
    )
    tags = db.relationship("Tag", secondary=task_tag, back_populates="tasks", lazy="selectin")
    attachments = db.relationship(
        "TaskAttachment",
        backref="task",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="TaskAttachment.created_at.asc()",
    )


class ChecklistItem(db.Model):
    """Single checklist row belonging to a task."""

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)


class TaskAttachment(db.Model):
    """Binary file attached to a task."""

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(255), nullable=False, default="application/octet-stream")
    size_bytes = db.Column(db.Integer, nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Project(db.Model):
    """User project used to group tasks."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(32), nullable=False, default=DEFAULT_PROJECT_ICON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tasks = db.relationship("Task", backref="project", lazy=True)


class Tag(db.Model):
    """User tag used for task categorization."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(16), nullable=False, default="#5b7cfa")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tasks = db.relationship("Task", secondary=task_tag, back_populates="tags")
