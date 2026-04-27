import base64
from datetime import datetime

from flask import request, url_for
from werkzeug.utils import secure_filename

from .constants import ATTACHMENT_FIELD_NAME, MAX_ATTACHMENT_BYTES, MAX_ATTACHMENTS_PER_TASK
from .extensions import db
from .models import Task, TaskAttachment
from .parsing import format_iso_datetime, parse_iso_datetime


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
        "download_url": url_for("attachments.download_attachment", attachment_id=attachment.id),
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
