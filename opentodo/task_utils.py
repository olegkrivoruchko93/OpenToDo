from flask import request

from .attachments import serialize_attachment
from .constants import PROJECT_ICON_MAP
from .extensions import db
from .models import Project, Tag, Task
from .parsing import parse_tag_color


def resolve_user_project(project_raw: str, user_id: int):
    project_value = (project_raw or "").strip()
    if not project_value:
        return None
    if not project_value.isdigit():
        return None
    return Project.query.filter_by(id=int(project_value), user_id=user_id).first()


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


def serialize_task(task: Task):
    due_at = task.due_at
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "due_at": due_at.strftime("%Y-%m-%dT%H:%M") if due_at else "",
        "due_date": due_at.date().isoformat() if due_at else (task.due_date.isoformat() if task.due_date else ""),
        "formatted_due_date": due_at.strftime("%d.%m.%Y %H:%M") if due_at else (
            task.due_date.strftime("%d.%m.%Y") if task.due_date else ""
        ),
        "telegram_notification_enabled": task.telegram_notification_enabled,
        "notification_sent_at": task.notification_sent_at.isoformat() if task.notification_sent_at else "",
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
