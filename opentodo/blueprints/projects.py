from flask import Blueprint, flash, g, redirect, request, url_for

from ..auth_utils import login_required
from ..extensions import db
from ..models import Project, Task
from ..navigation import redirect_to_current_view
from ..parsing import parse_project_icon


bp = Blueprint("projects", __name__)


@bp.route("/projects/add", methods=["POST"])
@login_required
def add_project():
    """Create a project for the current user."""
    name = request.form.get("name", "").strip()
    icon = parse_project_icon(request.form.get("icon", ""))
    if not name:
        flash("Название проекта не может быть пустым.")
        return redirect_to_current_view()

    existing = Project.query.filter(Project.user_id == g.user.id, db.func.lower(Project.name) == name.lower()).first()
    if existing:
        flash("Проект с таким названием уже существует.")
        return redirect_to_current_view()

    project = Project(name=name, icon=icon, user_id=g.user.id)
    db.session.add(project)
    db.session.commit()
    flash("Проект добавлен.")
    return redirect_to_current_view()


@bp.route("/projects/edit/<int:project_id>", methods=["POST"])
@login_required
def edit_project(project_id: int):
    """Update a project owned by the current user."""
    project = Project.query.filter_by(id=project_id, user_id=g.user.id).first_or_404()
    name = request.form.get("name", "").strip()
    icon = parse_project_icon(request.form.get("icon", ""))
    current_view = request.args.get("view", "inbox")
    search_query = (request.args.get("q") or request.form.get("q") or "").strip()

    if not name:
        flash("Название проекта не может быть пустым.")
        return redirect(url_for("main.index", view=current_view, project_id=project_id, q=search_query or None))

    duplicate = Project.query.filter(
        Project.user_id == g.user.id,
        db.func.lower(Project.name) == name.lower(),
        Project.id != project.id,
    ).first()
    if duplicate:
        flash("Проект с таким названием уже существует.")
        return redirect(url_for("main.index", view=current_view, project_id=project_id, q=search_query or None))

    project.name = name
    project.icon = icon
    db.session.commit()
    flash("Проект обновлен.")
    return redirect(url_for("main.index", view=current_view, project_id=project_id, q=search_query or None))


@bp.route("/projects/delete/<int:project_id>", methods=["POST"])
@login_required
def delete_project(project_id: int):
    """Delete a project and remove it from related tasks."""
    project = Project.query.filter_by(id=project_id, user_id=g.user.id).first_or_404()

    # Keep tasks, just clear project reference before deletion.
    Task.query.filter_by(user_id=g.user.id, project_id=project.id).update({Task.project_id: None})
    db.session.delete(project)
    db.session.commit()
    flash("Проект удален, привязка задач очищена.")

    current_view = request.args.get("view", "inbox")
    selected_project_raw = request.args.get("selected_project_id", "")
    search_query = (request.args.get("q") or request.form.get("q") or "").strip()
    if selected_project_raw.isdigit() and int(selected_project_raw) == project_id:
        return redirect(url_for("main.index", view=current_view, q=search_query or None))
    return redirect(url_for("main.index", view=current_view, project_id=selected_project_raw or None, q=search_query or None))
