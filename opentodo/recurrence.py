from calendar import monthrange
from datetime import datetime, timedelta

from .constants import normalize_task_recurrence
from .extensions import db
from .models import ChecklistItem, Task


def calculate_next_due_at(due_at: datetime | None, recurrence: str | None) -> datetime | None:
    """Return the next due datetime for a supported recurrence rule."""
    normalized_recurrence = normalize_task_recurrence(recurrence)
    if due_at is None or normalized_recurrence is None:
        return None
    if normalized_recurrence == "daily":
        return due_at + timedelta(days=1)
    if normalized_recurrence == "weekly":
        return due_at + timedelta(weeks=1)
    if normalized_recurrence == "monthly":
        return _add_months(due_at, 1)
    if normalized_recurrence == "yearly":
        return _add_months(due_at, 12)
    return None


def create_next_recurring_task(task: Task) -> Task | None:
    """Create the next active task instance for a completed recurring task."""
    recurrence = normalize_task_recurrence(task.recurrence)
    next_due_at = calculate_next_due_at(task.due_at, recurrence)
    if recurrence is None or next_due_at is None:
        return None

    recurrence_parent_id = task.recurrence_parent_id or task.id
    existing_next_task = Task.query.filter_by(
        user_id=task.user_id,
        recurrence_parent_id=recurrence_parent_id,
        due_at=next_due_at,
    ).first()
    if existing_next_task is not None:
        return existing_next_task

    next_task = Task(
        title=task.title,
        description=task.description,
        due_date=next_due_at.date(),
        due_at=next_due_at,
        notification_sent_at=None,
        telegram_notification_enabled=task.telegram_notification_enabled,
        priority=task.priority,
        recurrence=recurrence,
        recurrence_parent_id=recurrence_parent_id,
        is_done=False,
        user_id=task.user_id,
        project_id=task.project_id,
    )
    db.session.add(next_task)
    db.session.flush()

    for item in task.checklist_items:
        db.session.add(
            ChecklistItem(
                task_id=next_task.id,
                title=item.title,
                is_done=False,
                position=item.position,
            )
        )
    next_task.tags = list(task.tags)
    return next_task


def _add_months(value: datetime, months_to_add: int) -> datetime:
    month_index = value.month - 1 + months_to_add
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
