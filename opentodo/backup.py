import csv
import io
import zipfile
from datetime import datetime, time

from .attachments import (
    create_attachment_from_backup,
    serialize_backup_attachment,
    validate_attachment_capacity,
)
from .constants import normalize_task_priority, normalize_task_recurrence
from .extensions import db
from .models import ChecklistItem, Project, Tag, Task
from .parsing import format_iso_datetime, parse_csv_bool, parse_due_at, parse_due_date, parse_iso_datetime, parse_project_icon, parse_tag_color


def collect_backup_payload(user_id: int) -> dict:
    """Collect all backup-supported data for a user into a JSON payload."""
    projects = Project.query.filter_by(user_id=user_id).order_by(Project.id.asc()).all()
    tags = Tag.query.filter_by(user_id=user_id).order_by(Tag.id.asc()).all()
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.id.asc()).all()
    return {
        "schema_version": 6,
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
                "due_at": format_iso_datetime(task.due_at),
                "notification_sent_at": format_iso_datetime(task.notification_sent_at),
                "telegram_notification_enabled": task.telegram_notification_enabled,
                "priority": normalize_task_priority(task.priority),
                "recurrence": normalize_task_recurrence(task.recurrence) or "",
                "recurrence_parent_id": task.recurrence_parent_id or "",
                "is_done": task.is_done,
                "is_archived": task.is_archived,
                "is_deleted": task.is_deleted,
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
    """Delete all backup-managed records that belong to a user."""
    tasks = Task.query.filter_by(user_id=user_id).all()
    for task in tasks:
        task.tags = []
        for attachment in task.attachments:
            db.session.delete(attachment)
    Task.query.filter_by(user_id=user_id).delete()
    Project.query.filter_by(user_id=user_id).delete()
    Tag.query.filter_by(user_id=user_id).delete()


def apply_json_backup(payload: dict, user_id: int, mode: str) -> dict:
    """Import a JSON backup payload for a user and return import statistics."""
    if not isinstance(payload, dict):
        raise ValueError("Некорректный формат JSON backup.")
    if mode not in {"merge", "replace"}:
        raise ValueError("Некорректный режим импорта.")

    if mode == "replace":
        clear_user_data(user_id)

    project_map: dict[int, Project] = {}
    tag_map: dict[int, Tag] = {}
    task_map: dict[int, Task] = {}
    pending_recurrence_parent_links: list[tuple[Task, int]] = []
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
        due_at = parse_due_at(task_raw.get("due_at", ""))
        due_date = due_at.date() if due_at else parse_due_date(task_raw.get("due_date", ""))
        if due_at is None and due_date is not None:
            due_at = datetime.combine(due_date, time(hour=9))
        recurrence = normalize_task_recurrence(task_raw.get("recurrence"))
        is_done = bool(task_raw.get("is_done", False))
        is_archived = bool(task_raw.get("is_archived", is_done))
        is_deleted = bool(task_raw.get("is_deleted", False))
        task = Task(
            title=title[:200],
            description=(task_raw.get("description") or "")[:5000],
            due_date=due_date,
            due_at=due_at,
            notification_sent_at=parse_iso_datetime(task_raw.get("notification_sent_at", ""))
            if task_raw.get("notification_sent_at")
            else None,
            telegram_notification_enabled=bool(task_raw.get("telegram_notification_enabled", True)),
            priority=normalize_task_priority(task_raw.get("priority")),
            recurrence=recurrence,
            is_done=is_done,
            is_archived=is_archived,
            is_deleted=is_deleted,
            created_at=parse_iso_datetime(task_raw.get("created_at", "")),
            user_id=user_id,
            project_id=project_obj.id if project_obj else None,
        )
        db.session.add(task)
        db.session.flush()
        stats["tasks"] += 1
        task_raw_id = task_raw.get("id")
        if isinstance(task_raw_id, int):
            task_map[task_raw_id] = task
        raw_recurrence_parent_id = task_raw.get("recurrence_parent_id")
        if isinstance(raw_recurrence_parent_id, int):
            pending_recurrence_parent_links.append((task, raw_recurrence_parent_id))

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

    for task, raw_parent_id in pending_recurrence_parent_links:
        parent_task = task_map.get(raw_parent_id)
        if parent_task is not None and parent_task.id != task.id:
            task.recurrence_parent_id = parent_task.id

    return stats


def build_backup_csv_zip(payload: dict) -> bytes:
    """Serialize a backup payload into a ZIP archive of CSV files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        csv_files = {
            "projects.csv": ["id", "name", "icon", "created_at"],
            "tags.csv": ["id", "name", "color", "created_at"],
            "tasks.csv": [
                "id",
                "title",
                "description",
                "due_date",
                "due_at",
                "notification_sent_at",
                "telegram_notification_enabled",
                "priority",
                "recurrence",
                "recurrence_parent_id",
                "is_done",
                "is_archived",
                "is_deleted",
                "created_at",
                "project_id",
            ],
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
                    "due_at": task.get("due_at", ""),
                    "notification_sent_at": task.get("notification_sent_at", ""),
                    "telegram_notification_enabled": task.get("telegram_notification_enabled", True),
                    "priority": normalize_task_priority(task.get("priority")),
                    "recurrence": normalize_task_recurrence(task.get("recurrence")) or "",
                    "recurrence_parent_id": task.get("recurrence_parent_id", ""),
                    "is_done": task.get("is_done", False),
                    "is_archived": task.get("is_archived", task.get("is_done", False)),
                    "is_deleted": task.get("is_deleted", False),
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
    """Parse a ZIP archive of backup CSV files into a JSON-style payload."""
    required = {"projects.csv", "tags.csv", "tasks.csv", "checklist_items.csv", "task_tags.csv"}
    payload = {"schema_version": 6, "exported_at": datetime.utcnow().isoformat(), "projects": [], "tags": [], "tasks": []}
    with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
        names = set(zf.namelist())
        if not required.issubset(names):
            missing = ", ".join(sorted(required - names))
            raise ValueError(f"В архиве отсутствуют обязательные файлы: {missing}")

        def read_csv(name: str):
            """Read one CSV file from the backup archive."""
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
            is_done = parse_csv_bool(row.get("is_done", ""))
            tasks_by_id[task_id] = {
                "id": task_id,
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "due_date": row.get("due_date", ""),
                "due_at": row.get("due_at", ""),
                "notification_sent_at": row.get("notification_sent_at", ""),
                "telegram_notification_enabled": parse_csv_bool(row.get("telegram_notification_enabled", "1")),
                "priority": normalize_task_priority(row.get("priority")),
                "recurrence": normalize_task_recurrence(row.get("recurrence")) or "",
                "recurrence_parent_id": int(row["recurrence_parent_id"])
                if (row.get("recurrence_parent_id") or "").isdigit()
                else "",
                "is_done": is_done,
                "is_archived": parse_csv_bool(row.get("is_archived", "1" if is_done else "")),
                "is_deleted": parse_csv_bool(row.get("is_deleted", "")),
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
