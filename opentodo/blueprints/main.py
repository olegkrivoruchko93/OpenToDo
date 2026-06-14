from datetime import date, datetime, time

from flask import Blueprint, flash, g, render_template, request, session
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from ..auth_utils import login_required
from ..constants import PROJECT_ICON_MAP, PROJECT_ICON_OPTIONS, TASK_PRIORITY_OPTIONS, TASK_RECURRENCE_OPTIONS
from ..extensions import db
from ..models import Project, Tag, Task
from ..navigation import redirect_to_current_view
from ..task_utils import resolve_user_project, serialize_task


bp = Blueprint("main", __name__)


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcards while keeping partial-match search."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@bp.route("/", methods=["GET"])
@login_required
def index():
    """Render the task list with current view, project, and tag filters."""
    current_view = (request.args.get("view", "inbox") or "inbox").strip()
    if current_view not in {"inbox", "today", "plans", "archive", "trash"}:
        current_view = "inbox"
    projects = Project.query.filter_by(user_id=g.user.id).order_by(Project.name.asc()).all()
    selected_project = resolve_user_project(request.args.get("project_id", ""), g.user.id)
    selected_project_id = selected_project.id if selected_project else None
    selected_tag_raw = (request.args.get("tag_id") or "").strip()
    selected_tag = Tag.query.filter_by(id=int(selected_tag_raw), user_id=g.user.id).first() if selected_tag_raw.isdigit() else None
    selected_tag_id = selected_tag.id if selected_tag else None
    search_query = (request.args.get("q") or "").strip()
    session["last_view"] = current_view
    session["last_project_id"] = str(selected_project_id) if selected_project_id is not None else ""
    session["last_tag_id"] = str(selected_tag_id) if selected_tag_id is not None else ""
    session["last_search_query"] = search_query
    tags = Tag.query.filter_by(user_id=g.user.id).order_by(Tag.name.asc()).all()
    tag_suggestion_names = [tag.name for tag in tags]
    tag_suggestion_items = [{"name": tag.name, "color": tag.color} for tag in tags]

    base_task_query = Task.query.filter_by(user_id=g.user.id)
    if selected_project_id is not None:
        base_task_query = base_task_query.filter(Task.project_id == selected_project_id)
    if selected_tag_id is not None:
        base_task_query = base_task_query.join(Task.tags).filter(Tag.id == selected_tag_id)
    if search_query:
        search_project = aliased(Project)
        search_tag = aliased(Tag)
        search_pattern = f"%{_escape_like(search_query.lower())}%"
        base_task_query = (
            base_task_query.outerjoin(search_project, Task.project)
            .outerjoin(search_tag, Task.tags)
            .filter(
                or_(
                    db.func.lower(Task.title).like(search_pattern, escape="\\"),
                    db.func.lower(Task.description).like(search_pattern, escape="\\"),
                    db.func.lower(search_project.name).like(search_pattern, escape="\\"),
                    db.func.lower(search_tag.name).like(search_pattern, escape="\\"),
                )
            )
            .distinct()
        )

    visible_task_query = base_task_query.filter(Task.is_archived.is_(False), Task.is_deleted.is_(False))
    active_task_query = visible_task_query.filter(Task.is_done.is_(False))
    task_query = active_task_query
    today = date.today()
    today_end = datetime.combine(today, time.max)

    if current_view == "trash":
        task_query = base_task_query.filter(Task.is_deleted.is_(True))
    elif current_view == "archive":
        task_query = base_task_query.filter(Task.is_archived.is_(True), Task.is_deleted.is_(False))
    elif current_view == "today":
        task_query = task_query.filter(Task.due_at.isnot(None), Task.due_at <= today_end)
    elif current_view == "plans":
        task_query = task_query.filter(Task.due_at.isnot(None), Task.due_at > today_end)

    tasks = task_query.order_by(Task.due_at.is_(None), Task.due_at.asc(), Task.created_at.desc()).all()
    task_payloads = {task.id: serialize_task(task) for task in tasks}
    inbox_count = active_task_query.count()
    today_count = active_task_query.filter(Task.due_at.isnot(None), Task.due_at <= today_end).count()
    plans_count = active_task_query.filter(Task.due_at.isnot(None), Task.due_at > today_end).count()
    archive_count = base_task_query.filter(Task.is_archived.is_(True), Task.is_deleted.is_(False)).count()

    theme_themes = ["default", "warm", "dark", "ocean", "forest", "violet", "autumn", "sky", "gravel"]
    theme_mapping = {
        "default": "Светлая",
        "warm": "Тёплая",
        "dark": "Тёмная",
        "ocean": "Океан",
        "forest": "Лес",
        "violet": "Фиолетовая",
        "autumn": "Осенняя",  # New
        "sky": "Небесная",   # New
        "gravel": "Гравийная", # New
    }

    page_title = "Входящие"
    if current_view == "today":
        page_title = "Сегодня"
    elif current_view == "plans":
        page_title = "Планы"
    elif current_view == "archive":
        page_title = "Архив"
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
        tag_suggestion_items=tag_suggestion_items,
        project_icon_map=PROJECT_ICON_MAP,
        project_icon_options=PROJECT_ICON_OPTIONS,
        task_priority_options=TASK_PRIORITY_OPTIONS,
        task_recurrence_options=TASK_RECURRENCE_OPTIONS,
        current_view=current_view,
        selected_project_id=selected_project_id,
        selected_tag_id=selected_tag_id,
        search_query=search_query,
        page_title=page_title,
        inbox_count=inbox_count,
        today_count=today_count,
        plans_count=plans_count,
        archive_count=archive_count,
        theme_themes=theme_themes,
        theme_mapping=theme_mapping
    )


@bp.route("/settings/telegram", methods=["POST"])
@login_required
def update_telegram_settings():
    """Save Telegram notification settings for the current user."""
    bot_token = (request.form.get("telegram_bot_token") or "").strip()
    chat_id = (request.form.get("telegram_chat_id") or "").strip()
    username = (request.form.get("telegram_username") or "").strip().lstrip("@")
    notifications_enabled = request.form.get("telegram_notifications_enabled") == "1"

    if chat_id and not chat_id.lstrip("-").isdigit():
        flash("Telegram chat id должен быть числом.")
        return redirect_to_current_view()

    g.user.telegram_bot_token = bot_token[:255] or None
    g.user.telegram_chat_id = chat_id or None
    g.user.telegram_username = username[:128] or None
    g.user.telegram_notifications_enabled = notifications_enabled and bool(chat_id) and bool(bot_token)
    if notifications_enabled and (not chat_id or not bot_token):
        flash("Укажите токен бота и Telegram chat id, чтобы включить уведомления.")
    else:
        flash("Настройки Telegram сохранены.")

    db.session.commit()
    return redirect_to_current_view()