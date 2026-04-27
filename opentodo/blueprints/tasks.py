from flask import Blueprint, flash, g, jsonify, redirect, request, session, url_for

from ..attachments import add_uploaded_attachments_to_task
from ..auth_utils import login_required
from ..extensions import db
from ..models import ChecklistItem, Task
from ..navigation import redirect_to_current_view
from ..parsing import parse_due_at
from ..task_utils import (
    parse_checklist_items_from_form,
    parse_tag_names_from_form,
    resolve_or_create_tags,
    resolve_user_project,
    serialize_task,
)


bp = Blueprint("tasks", __name__)


@bp.route("/add", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_at_raw = request.form.get("due_at") or request.form.get("due_date", "")
    due_at = parse_due_at(due_at_raw)
    project = resolve_user_project(request.form.get("project_id", ""), g.user.id)
    checklist_items = parse_checklist_items_from_form()
    tag_names = parse_tag_names_from_form()

    if request.form.get("project_id", "").strip() and project is None:
        flash("Выбран некорректный проект.")
        return redirect_to_current_view()
    if due_at_raw.strip() and due_at is None:
        flash("Указаны некорректные дата и время.")
        return redirect_to_current_view()

    if title:
        try:
            task = Task(
                title=title,
                description=description,
                due_date=due_at.date() if due_at else None,
                due_at=due_at,
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


@bp.route("/toggle/<int:task_id>", methods=["POST"])
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
            url_for("main.index", view=current_view, project_id=selected_project_raw or None, tag_id=selected_tag_raw or None)
        )
    return redirect_to_current_view()


@bp.route("/checklist/toggle/<int:item_id>", methods=["POST"])
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


@bp.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id: int):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect_to_current_view()


@bp.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id: int):
    task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
    if request.method == "GET":
        return redirect_to_current_view()

    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_at_raw = request.form.get("due_at") or request.form.get("due_date", "")
    due_at = parse_due_at(due_at_raw)
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
    if due_at_raw.strip() and due_at is None:
        if wants_json:
            return jsonify({"ok": False, "error": "Указаны некорректные дата и время."}), 400
        flash("Указаны некорректные дата и время.")
        return redirect_to_current_view()

    if not title:
        if wants_json:
            return jsonify({"ok": False, "error": "Название задачи не может быть пустым."}), 400
        flash("Название задачи не может быть пустым.")
        return redirect_to_current_view()

    try:
        task.title = title
        task.description = description
        if task.due_at != due_at:
            task.notification_sent_at = None
        task.due_date = due_at.date() if due_at else None
        task.due_at = due_at
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
                    is_done=is_done,
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
