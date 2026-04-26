import os
import base64
import csv
import hmac
import io
import json
import zipfile
from datetime import date, datetime
from functools import wraps
from secrets import token_urlsafe
from urllib.parse import urlparse

from flask import Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = os.environ.get("FLASK_TEMPLATES_AUTO_RELOAD", "").lower() in {"1", "true", "yes"}
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or token_urlsafe(32)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}

db = SQLAlchemy(app)

task_tag = db.Table(
    "task_tag",
    db.Column("task_id", db.Integer, db.ForeignKey("task.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)

PROJECT_ICON_OPTIONS = [
    ("folder", "📁 Папка"),
    ("work", "💼 Работа"),
    ("study", "📚 Учеба"),
    ("health", "💪 Здоровье"),
    ("home", "🏠 Дом"),
    ("idea", "💡 Идеи"),
    ("finance", "💰 Финансы"),
    ("travel", "✈️ Путешествия"),
]
PROJECT_ICON_MAP = {key: label.split(" ", 1)[0] for key, label in PROJECT_ICON_OPTIONS}
DEFAULT_PROJECT_ICON = "folder"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_TASK = 5
ATTACHMENT_FIELD_NAME = "attachments[]"
CSRF_SESSION_KEY = "_csrf_token"
CSRF_FIELD_NAME = "csrf_token"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")
    projects = db.relationship("Project", backref="owner", lazy=True, cascade="all, delete-orphan")
    tags = db.relationship("Tag", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    due_date = db.Column(db.Date, nullable=True)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
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
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)


class TaskAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(255), nullable=False, default="application/octet-stream")
    size_bytes = db.Column(db.Integer, nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(32), nullable=False, default=DEFAULT_PROJECT_ICON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tasks = db.relationship("Task", backref="project", lazy=True)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(16), nullable=False, default="#5b7cfa")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tasks = db.relationship("Task", secondary=task_tag, back_populates="tags")


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def get_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def is_valid_csrf_token() -> bool:
    expected_token = session.get(CSRF_SESSION_KEY)
    supplied_token = (
        request.form.get(CSRF_FIELD_NAME)
        or request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
    )
    return bool(
        expected_token
        and supplied_token
        and hmac.compare_digest(str(expected_token), str(supplied_token))
    )


@app.before_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None


@app.before_request
def validate_csrf_for_mutations():
    if request.method != "POST":
        return None
    if is_valid_csrf_token():
        return None
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": False, "error": "Недействительный CSRF-токен."}), 403
    abort(403)


@app.context_processor
def inject_current_user():
    return {"current_user": g.user, "csrf_token": get_csrf_token, "tag_color": parse_tag_color}


def resolve_user_project(project_raw: str, user_id: int):
    project_value = (project_raw or "").strip()
    if not project_value:
        return None
    if not project_value.isdigit():
        return None
    return Project.query.filter_by(id=int(project_value), user_id=user_id).first()


def parse_due_date(due_date_raw: str):
    raw_value = (due_date_raw or "").strip()
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def parse_project_icon(icon_raw: str) -> str:
    icon_key = (icon_raw or "").strip()
    if icon_key in PROJECT_ICON_MAP:
        return icon_key
    return DEFAULT_PROJECT_ICON


def parse_tag_color(color_raw: str) -> str:
    color = (color_raw or "").strip()
    if len(color) == 7 and color.startswith("#") and all(char in "0123456789abcdefABCDEF" for char in color[1:]):
        return color.lower()
    if len(color) == 4 and color.startswith("#") and all(char in "0123456789abcdefABCDEF" for char in color[1:]):
        red, green, blue = color[1], color[2], color[3]
        return f"#{red}{red}{green}{green}{blue}{blue}".lower()
    return "#5b7cfa"


def get_navigation_context():
    # Prefer explicit form fields from POST, fallback to query string.
    current_view = (request.form.get("view") or request.args.get("view") or "inbox").strip()
    if current_view not in {"inbox", "today", "plans", "trash"}:
        current_view = "inbox"
    selected_project_raw = (
        request.form.get("filter_project_id")
        or request.form.get("project_id")
        or request.args.get("project_id")
        or ""
    ).strip()
    if not selected_project_raw.isdigit():
        selected_project_raw = ""
    selected_tag_raw = (request.form.get("tag_id") or request.args.get("tag_id") or "").strip()
    if not selected_tag_raw.isdigit():
        selected_tag_raw = ""
    return current_view, selected_project_raw, selected_tag_raw


def redirect_to_current_view():
    referrer = (request.referrer or "").strip()
    if referrer:
        parsed_referrer = urlparse(referrer)
        current_host = request.host.split(":", 1)[0]
        if parsed_referrer.scheme in {"http", "https"} and parsed_referrer.hostname == current_host:
            return redirect(referrer)

    current_view, selected_project_raw, selected_tag_raw = get_navigation_context()
    return redirect(
        url_for("index", view=current_view, project_id=selected_project_raw or None, tag_id=selected_tag_raw or None)
    )


def parse_checklist_items_from_form():
    raw_items = request.form.getlist("checklist_items[]")
    cleaned_items = []
    for item in raw_items:
        title = (item or "").strip()
        if title:
            cleaned_items.append(title)
    return cleaned_items


def parse_tag_names_from_form():
    raw_value = (request.form.get("tag_names") or "").strip()
    if not raw_value:
        return []
    unique_names = []
    seen_lower = set()
    for part in raw_value.split(","):
        name = part.strip()
        if not name:
            continue
        normalized = name.lower()
        if normalized in seen_lower:
            continue
        seen_lower.add(normalized)
        unique_names.append(name[:64])
    return unique_names


def resolve_or_create_tags(user_id: int, tag_names: list[str]):
    if not tag_names:
        return []
    lowered_names = [name.lower() for name in tag_names]
    existing = Tag.query.filter(Tag.user_id == user_id, db.func.lower(Tag.name).in_(lowered_names)).all()
    by_lower = {tag.name.lower(): tag for tag in existing}
    resolved = []
    for name in tag_names:
        lower_name = name.lower()
        tag = by_lower.get(lower_name)
        if tag is None:
            tag = Tag(name=name, user_id=user_id)
            db.session.add(tag)
            db.session.flush()
            by_lower[lower_name] = tag
        resolved.append(tag)
    return resolved


def format_file_size(size_bytes: int) -> str:
    size = max(int(size_bytes or 0), 0)
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{size} {units[unit_index]}"
    return f"{value:.1f} {units[unit_index]}"


def normalize_attachment_filename(filename: str) -> str:
    raw_name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if raw_name:
        return raw_name[:255]
    safe_name = secure_filename(filename or "")
    return safe_name[:255] if safe_name else "attachment"


def serialize_attachment(attachment: TaskAttachment):
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "formatted_size": format_file_size(attachment.size_bytes),
        "download_url": url_for("download_attachment", attachment_id=attachment.id),
    }


def serialize_backup_attachment(attachment: TaskAttachment) -> dict:
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "created_at": format_iso_datetime(attachment.created_at),
        "content_base64": base64.b64encode(attachment.content).decode("ascii"),
    }


def get_uploaded_attachment_files(field_name: str = ATTACHMENT_FIELD_NAME):
    return [file for file in request.files.getlist(field_name) if file and file.filename]


def validate_attachment_capacity(existing_count: int, new_count: int) -> None:
    if existing_count + new_count > MAX_ATTACHMENTS_PER_TASK:
        raise ValueError(f"К задаче можно прикрепить не больше {MAX_ATTACHMENTS_PER_TASK} файлов.")


def create_attachment_from_bytes(filename: str, content_type: str, content: bytes, created_at: datetime | None = None):
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Файл «{normalize_attachment_filename(filename)}» больше лимита {format_file_size(MAX_ATTACHMENT_BYTES)}."
        )
    return TaskAttachment(
        filename=normalize_attachment_filename(filename),
        content_type=(content_type or "application/octet-stream")[:255],
        size_bytes=len(content),
        content=content,
        created_at=created_at or datetime.utcnow(),
    )


def add_uploaded_attachments_to_task(task: Task, existing_count: int = 0) -> int:
    files = get_uploaded_attachment_files()
    validate_attachment_capacity(existing_count, len(files))
    added_count = 0
    for file in files:
        content = file.read()
        attachment = create_attachment_from_bytes(file.filename, file.mimetype, content)
        attachment.task_id = task.id
        db.session.add(attachment)
        added_count += 1
    return added_count


def create_attachment_from_backup(raw_attachment: dict):
    if not isinstance(raw_attachment, dict):
        return None
    encoded = raw_attachment.get("content_base64") or ""
    try:
        content = base64.b64decode(encoded, validate=True)
    except Exception as error:
        raise ValueError("Некорректное содержимое вложения в backup.") from error
    size_bytes = raw_attachment.get("size_bytes")
    if isinstance(size_bytes, int) and size_bytes != len(content):
        raise ValueError("Размер вложения в backup не совпадает с содержимым.")
    return create_attachment_from_bytes(
        raw_attachment.get("filename") or "attachment",
        raw_attachment.get("content_type") or "application/octet-stream",
        content,
        parse_iso_datetime(raw_attachment.get("created_at", "")),
    )


def serialize_task(task: Task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date.isoformat() if task.due_date else "",
        "formatted_due_date": task.due_date.strftime("%d.%m.%Y") if task.due_date else "",
        "project_id": task.project_id if task.project_id else "",
        "project_name": task.project.name if task.project else "",
        "project_icon": PROJECT_ICON_MAP.get(task.project.icon, "📁") if task.project else "",
        "checklist_items": [
            {"id": item.id, "title": item.title, "is_done": item.is_done}
            for item in task.checklist_items
        ],
        "tags": [{"id": tag.id, "name": tag.name, "color": parse_tag_color(tag.color)} for tag in task.tags],
        "tag_names": ", ".join(tag.name for tag in task.tags),
        "attachments": [serialize_attachment(attachment) for attachment in task.attachments],
    }


def format_iso_datetime(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def parse_iso_datetime(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.utcnow()


def parse_csv_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def collect_backup_payload(user_id: int) -> dict:
    projects = Project.query.filter_by(user_id=user_id).order_by(Project.id.asc()).all()
    tags = Tag.query.filter_by(user_id=user_id).order_by(Tag.id.asc()).all()
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.id.asc()).all()
    return {
        "schema_version": 2,
        "exported_at": datetime.utcnow().isoformat(),
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "icon": project.icon,
                "created_at": format_iso_datetime(project.created_at),
            }
            for project in projects
        ],
        "tags": [
            {
                "id": tag.id,
                "name": tag.name,
                "color": tag.color,
                "created_at": format_iso_datetime(tag.created_at),
            }
            for tag in tags
        ],
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "due_date": task.due_date.isoformat() if task.due_date else "",
                "is_done": task.is_done,
                "created_at": format_iso_datetime(task.created_at),
                "project_id": task.project_id or "",
                "checklist_items": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "is_done": item.is_done,
                        "position": item.position,
                    }
                    for item in task.checklist_items
                ],
                "tag_ids": [tag.id for tag in task.tags],
                "attachments": [serialize_backup_attachment(attachment) for attachment in task.attachments],
            }
            for task in tasks
        ],
    }


def clear_user_data(user_id: int) -> None:
    tasks = Task.query.filter_by(user_id=user_id).all()
    for task in tasks:
        task.tags = []
        for attachment in task.attachments:
            db.session.delete(attachment)
    Task.query.filter_by(user_id=user_id).delete()
    Project.query.filter_by(user_id=user_id).delete()
    Tag.query.filter_by(user_id=user_id).delete()


def apply_json_backup(payload: dict, user_id: int, mode: str) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Некорректный формат JSON backup.")
    if mode not in {"merge", "replace"}:
        raise ValueError("Некорректный режим импорта.")

    if mode == "replace":
        clear_user_data(user_id)

    project_map: dict[int, Project] = {}
    tag_map: dict[int, Tag] = {}
    stats = {"projects": 0, "tags": 0, "tasks": 0, "checklist_items": 0, "task_tag_links": 0, "attachments": 0}

    for project_raw in payload.get("projects", []):
        name = (project_raw.get("name") or "").strip()
        if not name:
            continue
        existing = Project.query.filter(Project.user_id == user_id, db.func.lower(Project.name) == name.lower()).first()
        if existing is None:
            existing = Project(
                name=name[:120],
                icon=parse_project_icon(project_raw.get("icon", "")),
                user_id=user_id,
                created_at=parse_iso_datetime(project_raw.get("created_at", "")),
            )
            db.session.add(existing)
            db.session.flush()
            stats["projects"] += 1
        project_raw_id = project_raw.get("id")
        if isinstance(project_raw_id, int):
            project_map[project_raw_id] = existing

    for tag_raw in payload.get("tags", []):
        name = (tag_raw.get("name") or "").strip()
        if not name:
            continue
        existing = Tag.query.filter(Tag.user_id == user_id, db.func.lower(Tag.name) == name.lower()).first()
        if existing is None:
            existing = Tag(
                name=name[:64],
                color=parse_tag_color(tag_raw.get("color", "")),
                user_id=user_id,
                created_at=parse_iso_datetime(tag_raw.get("created_at", "")),
            )
            db.session.add(existing)
            db.session.flush()
            stats["tags"] += 1
        tag_raw_id = tag_raw.get("id")
        if isinstance(tag_raw_id, int):
            tag_map[tag_raw_id] = existing

    for task_raw in payload.get("tasks", []):
        title = (task_raw.get("title") or "").strip()
        if not title:
            continue
        project_obj = None
        raw_project_id = task_raw.get("project_id")
        if isinstance(raw_project_id, int):
            project_obj = project_map.get(raw_project_id)
        due_date = parse_due_date(task_raw.get("due_date", ""))
        task = Task(
            title=title[:200],
            description=(task_raw.get("description") or "")[:5000],
            due_date=due_date,
            is_done=bool(task_raw.get("is_done", False)),
            created_at=parse_iso_datetime(task_raw.get("created_at", "")),
            user_id=user_id,
            project_id=project_obj.id if project_obj else None,
        )
        db.session.add(task)
        db.session.flush()
        stats["tasks"] += 1

        for item_raw in task_raw.get("checklist_items", []):
            item_title = (item_raw.get("title") or "").strip()
            if not item_title:
                continue
            db.session.add(
                ChecklistItem(
                    task_id=task.id,
                    title=item_title[:255],
                    is_done=bool(item_raw.get("is_done", False)),
                    position=int(item_raw.get("position") or 0),
                )
            )
            stats["checklist_items"] += 1

        tag_ids = task_raw.get("tag_ids", [])
        if isinstance(tag_ids, list):
            for raw_tag_id in tag_ids:
                if isinstance(raw_tag_id, int):
                    tag_obj = tag_map.get(raw_tag_id)
                    if tag_obj is not None and tag_obj not in task.tags:
                        task.tags.append(tag_obj)
                        stats["task_tag_links"] += 1

        raw_attachments = task_raw.get("attachments", [])
        if isinstance(raw_attachments, list):
            validate_attachment_capacity(0, len(raw_attachments))
            for attachment_raw in raw_attachments:
                attachment = create_attachment_from_backup(attachment_raw)
                if attachment is None:
                    continue
                attachment.task_id = task.id
                db.session.add(attachment)
                stats["attachments"] += 1

    return stats


def build_backup_csv_zip(payload: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        csv_files = {
            "projects.csv": ["id", "name", "icon", "created_at"],
            "tags.csv": ["id", "name", "color", "created_at"],
            "tasks.csv": ["id", "title", "description", "due_date", "is_done", "created_at", "project_id"],
            "checklist_items.csv": ["task_id", "title", "is_done", "position"],
            "task_tags.csv": ["task_id", "tag_id"],
            "attachments.csv": ["task_id", "filename", "content_type", "size_bytes", "created_at", "content_base64"],
        }
        rows_by_file = {name: [] for name in csv_files}
        rows_by_file["projects.csv"] = payload.get("projects", [])
        rows_by_file["tags.csv"] = payload.get("tags", [])
        for task in payload.get("tasks", []):
            rows_by_file["tasks.csv"].append(
                {
                    "id": task.get("id", ""),
                    "title": task.get("title", ""),
                    "description": task.get("description", ""),
                    "due_date": task.get("due_date", ""),
                    "is_done": task.get("is_done", False),
                    "created_at": task.get("created_at", ""),
                    "project_id": task.get("project_id", ""),
                }
            )
            for item in task.get("checklist_items", []):
                rows_by_file["checklist_items.csv"].append(
                    {
                        "task_id": task.get("id", ""),
                        "title": item.get("title", ""),
                        "is_done": item.get("is_done", False),
                        "position": item.get("position", 0),
                    }
                )
            for tag_id in task.get("tag_ids", []):
                rows_by_file["task_tags.csv"].append({"task_id": task.get("id", ""), "tag_id": tag_id})
            for attachment in task.get("attachments", []):
                rows_by_file["attachments.csv"].append(
                    {
                        "task_id": task.get("id", ""),
                        "filename": attachment.get("filename", ""),
                        "content_type": attachment.get("content_type", ""),
                        "size_bytes": attachment.get("size_bytes", ""),
                        "created_at": attachment.get("created_at", ""),
                        "content_base64": attachment.get("content_base64", ""),
                    }
                )

        for filename, headers in csv_files.items():
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            for row in rows_by_file[filename]:
                writer.writerow({header: row.get(header, "") for header in headers})
            zf.writestr(filename, "\ufeff" + stream.getvalue())
    buffer.seek(0)
    return buffer.getvalue()


def parse_csv_zip_to_payload(file_bytes: bytes) -> dict:
    required = {"projects.csv", "tags.csv", "tasks.csv", "checklist_items.csv", "task_tags.csv"}
    payload = {"schema_version": 2, "exported_at": datetime.utcnow().isoformat(), "projects": [], "tags": [], "tasks": []}
    with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
        names = set(zf.namelist())
        if not required.issubset(names):
            missing = ", ".join(sorted(required - names))
            raise ValueError(f"В архиве отсутствуют обязательные файлы: {missing}")

        def read_csv(name: str):
            with zf.open(name, "r") as raw:
                decoded = raw.read().decode("utf-8-sig")
                return list(csv.DictReader(io.StringIO(decoded)))

        projects = read_csv("projects.csv")
        tags = read_csv("tags.csv")
        tasks = read_csv("tasks.csv")
        checklist_rows = read_csv("checklist_items.csv")
        task_tag_rows = read_csv("task_tags.csv")
        attachment_rows = read_csv("attachments.csv") if "attachments.csv" in names else []

        payload["projects"] = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "icon": row.get("icon", ""),
                "created_at": row.get("created_at", ""),
            }
            for row in projects
            if (row.get("id") or "").isdigit()
        ]
        payload["tags"] = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "color": parse_tag_color(row.get("color", "")),
                "created_at": row.get("created_at", ""),
            }
            for row in tags
            if (row.get("id") or "").isdigit()
        ]

        tasks_by_id = {}
        for row in tasks:
            task_id_raw = (row.get("id") or "").strip()
            if not task_id_raw.isdigit():
                continue
            task_id = int(task_id_raw)
            tasks_by_id[task_id] = {
                "id": task_id,
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "due_date": row.get("due_date", ""),
                "is_done": parse_csv_bool(row.get("is_done", "")),
                "created_at": row.get("created_at", ""),
                "project_id": int(row["project_id"]) if (row.get("project_id") or "").isdigit() else "",
                "checklist_items": [],
                "tag_ids": [],
                "attachments": [],
            }

        for row in checklist_rows:
            task_id_raw = (row.get("task_id") or "").strip()
            if not task_id_raw.isdigit():
                continue
            task = tasks_by_id.get(int(task_id_raw))
            if task is None:
                continue
            task["checklist_items"].append(
                {
                    "title": row.get("title", ""),
                    "is_done": parse_csv_bool(row.get("is_done", "")),
                    "position": int(row.get("position") or 0),
                }
            )

        for row in task_tag_rows:
            task_id_raw = (row.get("task_id") or "").strip()
            tag_id_raw = (row.get("tag_id") or "").strip()
            if not task_id_raw.isdigit() or not tag_id_raw.isdigit():
                continue
            task = tasks_by_id.get(int(task_id_raw))
            if task is None:
                continue
            task["tag_ids"].append(int(tag_id_raw))

        for row in attachment_rows:
            task_id_raw = (row.get("task_id") or "").strip()
            if not task_id_raw.isdigit():
                continue
            task = tasks_by_id.get(int(task_id_raw))
            if task is None:
                continue
            size_raw = (row.get("size_bytes") or "").strip()
            task["attachments"].append(
                {
                    "filename": row.get("filename", ""),
                    "content_type": row.get("content_type", ""),
                    "size_bytes": int(size_raw) if size_raw.isdigit() else None,
                    "created_at": row.get("created_at", ""),
                    "content_base64": row.get("content_base64", ""),
                }
            )

        payload["tasks"] = list(tasks_by_id.values())
    return payload


@app.route("/", methods=["GET"])
@login_required
def index():
    current_view = (request.args.get("view", "inbox") or "inbox").strip()
    if current_view not in {"inbox", "today", "plans", "trash"}:
        current_view = "inbox"
    projects = Project.query.filter_by(user_id=g.user.id).order_by(Project.name.asc()).all()
    selected_project = resolve_user_project(request.args.get("project_id", ""), g.user.id)
    selected_project_id = selected_project.id if selected_project else None
    selected_tag_raw = (request.args.get("tag_id") or "").strip()
    selected_tag = Tag.query.filter_by(id=int(selected_tag_raw), user_id=g.user.id).first() if selected_tag_raw.isdigit() else None
    selected_tag_id = selected_tag.id if selected_tag else None
    session["last_view"] = current_view
    session["last_project_id"] = str(selected_project_id) if selected_project_id is not None else ""
    session["last_tag_id"] = str(selected_tag_id) if selected_tag_id is not None else ""
    tags = Tag.query.filter_by(user_id=g.user.id).order_by(Tag.name.asc()).all()
    tag_suggestion_names = [tag.name for tag in tags]

    base_task_query = Task.query.filter_by(user_id=g.user.id)
    if selected_project_id is not None:
        base_task_query = base_task_query.filter(Task.project_id == selected_project_id)
    if selected_tag_id is not None:
        base_task_query = base_task_query.join(Task.tags).filter(Tag.id == selected_tag_id)

    task_query = base_task_query
    today = date.today()

    if current_view == "trash":
        task_query = task_query.filter(Task.is_done.is_(True))
    elif current_view == "today":
        task_query = task_query.filter(Task.due_date.isnot(None), Task.due_date <= today)
    elif current_view == "plans":
        task_query = task_query.filter(Task.due_date.isnot(None), Task.due_date > today)

    tasks = task_query.order_by(Task.created_at.desc()).all()
    task_payloads = {task.id: serialize_task(task) for task in tasks}
    inbox_count = base_task_query.count()
    today_count = base_task_query.filter(Task.due_date.isnot(None), Task.due_date <= today).count()
    plans_count = base_task_query.filter(Task.due_date.isnot(None), Task.due_date > today).count()
    page_title = "Входящие"
    if current_view == "today":
        page_title = "Сегодня"
    elif current_view == "plans":
        page_title = "Планы"
    elif current_view == "trash":
        page_title = "Корзина"
    if selected_project is not None:
        page_title = f"{page_title}: {selected_project.name}"
    if selected_tag is not None:
        page_title = f"{page_title} #{selected_tag.name}"
    return render_template(
        "index.html",
        tasks=tasks,
        task_payloads=task_payloads,
        projects=projects,
        tags=tags,
        tag_suggestion_names=tag_suggestion_names,
        project_icon_map=PROJECT_ICON_MAP,
        project_icon_options=PROJECT_ICON_OPTIONS,
        current_view=current_view,
        selected_project_id=selected_project_id,
        selected_tag_id=selected_tag_id,
        page_title=page_title,
        inbox_count=inbox_count,
        today_count=today_count,
        plans_count=plans_count,
    )


@app.route("/backup/export/json", methods=["GET", "POST"])
@login_required
def export_backup_json():
    payload = collect_backup_payload(g.user.id)
    file_name = f"opentodo-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    response = Response(body, mimetype="application/json")
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@app.route("/backup/export/csv", methods=["GET", "POST"])
@login_required
def export_backup_csv():
    payload = collect_backup_payload(g.user.id)
    file_name = f"opentodo-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
    csv_zip = build_backup_csv_zip(payload)
    response = Response(csv_zip, mimetype="application/zip")
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@app.route("/backup/import/json", methods=["POST"])
@login_required
def import_backup_json():
    mode = (request.form.get("mode") or "merge").strip().lower()
    file = request.files.get("backup_file")
    if file is None or not file.filename:
        flash("Выберите JSON файл для импорта.")
        return redirect_to_current_view()
    try:
        payload = json.loads(file.read().decode("utf-8-sig"))
        stats = apply_json_backup(payload, g.user.id, mode)
        db.session.commit()
        flash(
            "Импорт JSON завершен. "
            f"Проекты: {stats['projects']}, метки: {stats['tags']}, задачи: {stats['tasks']}, "
            f"чеклист: {stats['checklist_items']}, вложения: {stats['attachments']}."
        )
    except Exception as error:
        db.session.rollback()
        flash(f"Ошибка импорта JSON: {error}")
    return redirect_to_current_view()


@app.route("/backup/import/csv", methods=["POST"])
@login_required
def import_backup_csv():
    mode = (request.form.get("mode") or "merge").strip().lower()
    file = request.files.get("backup_file")
    if file is None or not file.filename:
        flash("Выберите ZIP CSV файл для импорта.")
        return redirect_to_current_view()
    try:
        payload = parse_csv_zip_to_payload(file.read())
        stats = apply_json_backup(payload, g.user.id, mode)
        db.session.commit()
        flash(
            "Импорт CSV завершен. "
            f"Проекты: {stats['projects']}, метки: {stats['tags']}, задачи: {stats['tasks']}, "
            f"чеклист: {stats['checklist_items']}, вложения: {stats['attachments']}."
        )
    except Exception as error:
        db.session.rollback()
        flash(f"Ошибка импорта CSV: {error}")
    return redirect_to_current_view()


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Введите логин и пароль.")
        elif User.query.filter_by(username=username).first():
            flash("Пользователь с таким логином уже существует.")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Регистрация успешна. Теперь войдите в аккаунт.")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Неверный логин или пароль.")
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/projects/add", methods=["POST"])
@login_required
def add_project():
    name = request.form.get("name", "").strip()
    icon = parse_project_icon(request.form.get("icon", ""))
    if not name:
        flash("Название проекта не может быть пустым.")
        return redirect(url_for("index"))

    existing = Project.query.filter(Project.user_id == g.user.id, db.func.lower(Project.name) == name.lower()).first()
    if existing:
        flash("Проект с таким названием уже существует.")
        return redirect(url_for("index"))

    project = Project(name=name, icon=icon, user_id=g.user.id)
    db.session.add(project)
    db.session.commit()
    flash("Проект добавлен.")
    return redirect(url_for("index"))


@app.route("/projects/edit/<int:project_id>", methods=["POST"])
@login_required
def edit_project(project_id: int):
    project = Project.query.filter_by(id=project_id, user_id=g.user.id).first_or_404()
    name = request.form.get("name", "").strip()
    icon = parse_project_icon(request.form.get("icon", ""))

    if not name:
        flash("Название проекта не может быть пустым.")
        return redirect(url_for("index", view=request.args.get("view", "inbox"), project_id=project_id))

    duplicate = Project.query.filter(
        Project.user_id == g.user.id,
        db.func.lower(Project.name) == name.lower(),
        Project.id != project.id,
    ).first()
    if duplicate:
        flash("Проект с таким названием уже существует.")
        return redirect(url_for("index", view=request.args.get("view", "inbox"), project_id=project_id))

    project.name = name
    project.icon = icon
    db.session.commit()
    flash("Проект обновлен.")
    return redirect(url_for("index", view=request.args.get("view", "inbox"), project_id=project_id))


@app.route("/projects/delete/<int:project_id>", methods=["POST"])
@login_required
def delete_project(project_id: int):
    project = Project.query.filter_by(id=project_id, user_id=g.user.id).first_or_404()

    # Keep tasks, just clear project reference before deletion.
    Task.query.filter_by(user_id=g.user.id, project_id=project.id).update({Task.project_id: None})
    db.session.delete(project)
    db.session.commit()
    flash("Проект удален, привязка задач очищена.")

    current_view = request.args.get("view", "inbox")
    selected_project_raw = request.args.get("selected_project_id", "")
    if selected_project_raw.isdigit() and int(selected_project_raw) == project_id:
        return redirect(url_for("index", view=current_view))
    return redirect(url_for("index", view=current_view, project_id=selected_project_raw or None))


@app.route("/tags/add", methods=["POST"])
@login_required
def add_tag():
    name = (request.form.get("name") or "").strip()
    color = parse_tag_color(request.form.get("color", ""))
    if not name:
        flash("Название метки не может быть пустым.")
        return redirect_to_current_view()
    duplicate = Tag.query.filter(Tag.user_id == g.user.id, db.func.lower(Tag.name) == name.lower()).first()
    if duplicate:
        flash("Метка с таким названием уже существует.")
        return redirect_to_current_view()
    db.session.add(Tag(name=name[:64], color=color, user_id=g.user.id))
    db.session.commit()
    flash("Метка добавлена.")
    return redirect_to_current_view()


@app.route("/tags/edit/<int:tag_id>", methods=["POST"])
@login_required
def edit_tag(tag_id: int):
    tag = Tag.query.filter_by(id=tag_id, user_id=g.user.id).first_or_404()
    name = (request.form.get("name") or "").strip()
    color = parse_tag_color(request.form.get("color", tag.color))
    if not name:
        flash("Название метки не может быть пустым.")
        return redirect_to_current_view()
    duplicate = Tag.query.filter(
        Tag.user_id == g.user.id, db.func.lower(Tag.name) == name.lower(), Tag.id != tag.id
    ).first()
    if duplicate:
        flash("Метка с таким названием уже существует.")
        return redirect_to_current_view()
    tag.name = name[:64]
    tag.color = color
    db.session.commit()
    flash("Метка обновлена.")
    return redirect_to_current_view()


@app.route("/tags/delete/<int:tag_id>", methods=["POST"])
@login_required
def delete_tag(tag_id: int):
    tag = Tag.query.filter_by(id=tag_id, user_id=g.user.id).first_or_404()
    tag.tasks.clear()
    db.session.delete(tag)
    db.session.commit()
    flash("Метка удалена.")
    return redirect_to_current_view()


@app.route("/add", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = parse_due_date(request.form.get("due_date", ""))
    project = resolve_user_project(request.form.get("project_id", ""), g.user.id)
    checklist_items = parse_checklist_items_from_form()
    tag_names = parse_tag_names_from_form()

    if request.form.get("project_id", "").strip() and project is None:
        flash("Выбран некорректный проект.")
        return redirect_to_current_view()
    if request.form.get("due_date", "").strip() and due_date is None:
        flash("Указана некорректная дата.")
        return redirect_to_current_view()

    if title:
        try:
            task = Task(
                title=title,
                description=description,
                due_date=due_date,
                user_id=g.user.id,
                project_id=project.id if project else None,
            )
            db.session.add(task)
            db.session.flush()
            for position, item_title in enumerate(checklist_items):
                db.session.add(
                    ChecklistItem(
                        task_id=task.id,
                        title=item_title,
                        position=position,
                    )
                )
            task.tags = resolve_or_create_tags(g.user.id, tag_names)
            add_uploaded_attachments_to_task(task)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error))
    return redirect_to_current_view()


@app.route("/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle_task(task_id: int) -> object:
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    task.is_done = not task.is_done
    db.session.commit()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "is_done": task.is_done})
    current_view = (
        request.form.get("view")
        or request.args.get("view")
        or session.get("last_view")
        or ""
    ).strip()
    selected_project_raw = (
        request.form.get("project_id")
        or request.args.get("project_id")
        or session.get("last_project_id")
        or ""
    ).strip()
    selected_tag_raw = (
        request.form.get("tag_id")
        or request.args.get("tag_id")
        or session.get("last_tag_id")
        or ""
    ).strip()
    if current_view in {"inbox", "today", "plans", "trash"}:
        if not selected_project_raw.isdigit():
            selected_project_raw = ""
        if not selected_tag_raw.isdigit():
            selected_tag_raw = ""
        return redirect(
            url_for("index", view=current_view, project_id=selected_project_raw or None, tag_id=selected_tag_raw or None)
        )
    return redirect_to_current_view()


@app.route("/checklist/toggle/<int:item_id>", methods=["POST"])
@login_required
def toggle_checklist_item(item_id: int):
    checklist_item = (
        ChecklistItem.query.join(Task, ChecklistItem.task_id == Task.id)
        .filter(ChecklistItem.id == item_id, Task.user_id == g.user.id)
        .first_or_404()
    )
    checklist_item.is_done = not checklist_item.is_done
    db.session.commit()
    return redirect_to_current_view()


@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id: int):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect_to_current_view()


@app.route("/attachments/<int:attachment_id>/download", methods=["GET"])
@login_required
def download_attachment(attachment_id: int):
    attachment = (
        TaskAttachment.query.join(Task, TaskAttachment.task_id == Task.id)
        .filter(TaskAttachment.id == attachment_id, Task.user_id == g.user.id)
        .first_or_404()
    )
    return send_file(
        io.BytesIO(attachment.content),
        mimetype=attachment.content_type or "application/octet-stream",
        as_attachment=True,
        download_name=attachment.filename,
    )


@app.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id: int):
    attachment = (
        TaskAttachment.query.join(Task, TaskAttachment.task_id == Task.id)
        .filter(TaskAttachment.id == attachment_id, Task.user_id == g.user.id)
        .first_or_404()
    )
    db.session.delete(attachment)
    db.session.commit()
    flash("Вложение удалено.")
    return redirect_to_current_view()


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id: int):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    if request.method == "GET":
        return redirect_to_current_view()

    if request.method == "POST":
        wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = parse_due_date(request.form.get("due_date", ""))
        project = resolve_user_project(request.form.get("project_id", ""), g.user.id)
        checklist_titles = request.form.getlist("checklist_items[]")
        checklist_item_ids = request.form.getlist("checklist_item_id[]")
        checklist_done_values = request.form.getlist("checklist_item_done[]")
        tag_names = parse_tag_names_from_form()

        if request.form.get("project_id", "").strip() and project is None:
            if wants_json:
                return jsonify({"ok": False, "error": "Выбран некорректный проект."}), 400
            flash("Выбран некорректный проект.")
            return redirect_to_current_view()
        if request.form.get("due_date", "").strip() and due_date is None:
            if wants_json:
                return jsonify({"ok": False, "error": "Указана некорректная дата."}), 400
            flash("Указана некорректная дата.")
            return redirect_to_current_view()

        if not title:
            if wants_json:
                return jsonify({"ok": False, "error": "Название задачи не может быть пустым."}), 400
            flash("Название задачи не может быть пустым.")
            return redirect_to_current_view()

        try:
            task.title = title
            task.description = description
            task.due_date = due_date
            task.project_id = project.id if project else None
            task.tags = resolve_or_create_tags(g.user.id, tag_names)
            existing_items_by_id = {item.id: item for item in task.checklist_items}
            kept_item_ids = set()
            next_position = 0
            for index, raw_title in enumerate(checklist_titles):
                item_title = (raw_title or "").strip()
                if not item_title:
                    continue

                item_id_raw = checklist_item_ids[index].strip() if index < len(checklist_item_ids) else ""
                done_raw = checklist_done_values[index].strip() if index < len(checklist_done_values) else "0"
                is_done = done_raw == "1"

                if item_id_raw.isdigit():
                    item_id = int(item_id_raw)
                    item = existing_items_by_id.get(item_id)
                    if item is not None:
                        item.title = item_title
                        item.position = next_position
                        item.is_done = is_done
                        kept_item_ids.add(item_id)
                        next_position += 1
                        continue

                db.session.add(
                    ChecklistItem(
                        task_id=task.id,
                        title=item_title,
                        is_done=False,
                        position=next_position,
                    )
                )
                next_position += 1

            for existing_item in existing_items_by_id.values():
                if existing_item.id not in kept_item_ids:
                    db.session.delete(existing_item)

            raw_delete_attachment_ids = (
                request.form.getlist("delete_attachment_ids[]") + request.form.getlist("delete_attachment_ids")
            )
            delete_attachment_ids = {
                int(raw_id.strip())
                for raw_id in raw_delete_attachment_ids
                if raw_id and raw_id.strip().isdigit()
            }
            deleted_attachment_count = 0
            if delete_attachment_ids:
                for attachment in task.attachments:
                    if attachment.id in delete_attachment_ids:
                        db.session.delete(attachment)
                        deleted_attachment_count += 1

            existing_attachment_count = max(len(task.attachments) - deleted_attachment_count, 0)
            add_uploaded_attachments_to_task(task, existing_attachment_count)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            if wants_json:
                return jsonify({"ok": False, "error": str(error)}), 400
            flash(str(error))
            return redirect_to_current_view()
        if wants_json:
            return jsonify({"ok": True, "task": serialize_task(task)})
        flash("Задача обновлена.")
        return redirect_to_current_view()


def init_db() -> None:
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if not inspector.has_table("project"):
            db.session.execute(
                text(
                    "CREATE TABLE project ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(120) NOT NULL, "
                    "icon VARCHAR(32) NOT NULL DEFAULT 'folder', "
                    "created_at DATETIME NOT NULL, "
                    "user_id INTEGER NOT NULL)"
                )
            )
            db.session.commit()
        project_columns = {column["name"] for column in inspector.get_columns("project")}
        if "icon" not in project_columns:
            db.session.execute(text("ALTER TABLE project ADD COLUMN icon VARCHAR(32) DEFAULT 'folder'"))
            db.session.execute(text("UPDATE project SET icon = 'folder' WHERE icon IS NULL OR icon = ''"))
            db.session.commit()
        task_columns = {column["name"] for column in inspector.get_columns("task")}
        if "user_id" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN user_id INTEGER"))
            db.session.commit()
        if "description" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN description TEXT DEFAULT ''"))
            db.session.execute(text("UPDATE task SET description = '' WHERE description IS NULL"))
            db.session.commit()
        if "project_id" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN project_id INTEGER"))
            db.session.commit()
        if "due_date" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN due_date DATE"))
            db.session.commit()
        if not inspector.has_table("checklist_item"):
            db.session.execute(
                text(
                    "CREATE TABLE checklist_item ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "task_id INTEGER NOT NULL, "
                    "title VARCHAR(255) NOT NULL, "
                    "is_done BOOLEAN NOT NULL DEFAULT 0, "
                    "position INTEGER NOT NULL DEFAULT 0)"
                )
            )
            db.session.commit()
        if not inspector.has_table("task_attachment"):
            db.session.execute(
                text(
                    "CREATE TABLE task_attachment ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "task_id INTEGER NOT NULL, "
                    "filename VARCHAR(255) NOT NULL, "
                    "content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream', "
                    "size_bytes INTEGER NOT NULL, "
                    "content BLOB NOT NULL, "
                    "created_at DATETIME NOT NULL)"
                )
            )
            db.session.commit()
        db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_task_attachment_task_id ON task_attachment(task_id)"))
        db.session.commit()
        if not inspector.has_table("tag"):
            db.session.execute(
                text(
                    "CREATE TABLE tag ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(64) NOT NULL, "
                    "color VARCHAR(16) NOT NULL DEFAULT '#5b7cfa', "
                    "created_at DATETIME NOT NULL, "
                    "user_id INTEGER NOT NULL)"
                )
            )
            db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_tag_user_name ON tag(user_id, name)"))
            db.session.commit()
        tag_columns = {column["name"] for column in inspector.get_columns("tag")} if inspector.has_table("tag") else set()
        if inspector.has_table("tag") and "color" not in tag_columns:
            db.session.execute(text("ALTER TABLE tag ADD COLUMN color VARCHAR(16) DEFAULT '#5b7cfa'"))
            db.session.execute(text("UPDATE tag SET color = '#5b7cfa' WHERE color IS NULL OR color = ''"))
            db.session.commit()
        if not inspector.has_table("task_tag"):
            db.session.execute(
                text(
                    "CREATE TABLE task_tag ("
                    "task_id INTEGER NOT NULL, "
                    "tag_id INTEGER NOT NULL, "
                    "PRIMARY KEY (task_id, tag_id))"
                )
            )
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_task_tag_task_id ON task_tag(task_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_task_tag_tag_id ON task_tag(tag_id)"))
            db.session.commit()


if __name__ == "__main__":
    init_db()
    app.run(host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"), debug=False)
