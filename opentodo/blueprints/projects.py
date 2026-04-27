from flask import Blueprint, flash, g, redirect, request, url_for

from ..auth_utils import login_required
from ..extensions import db
from ..models import Project, Task
from ..parsing import parse_project_icon


bp = Blueprint("projects", __name__)


@bp.route("/projects/add", methods=["POST"])
@login_required
def add_project():
    name = request.form.get("name", "").strip()
    icon = parse_project_icon(request.form.get("icon", ""))
    if not name:
        flash("Название проекта не может быть пустым.")
        return redirect(url_for("main.index"))

    existing = Project.query.filter(Project.user_id == g.user.id, db.func.lower(Project.name) == name.lower()).first()
    if existing:
        flash("Проект с таким названием уже существует.")
        return redirect(url_for("main.index"))

    project = Project(name=name, icon=icon, user_id=g.user.id)
    db.session.add(project)
    db.session.commit()
    flash("Проект добавлен.")
    return redirect(url_for("main.index"))


@bp.route("/projects/edit/<int:project_id>", methods=["POST"])
@login_required
def edit_project(project_id: int):
    project = Project.query.filter_by(id=project_id, user_id=g.user.id).first_or_404()
    name = request.form.get("name", "").strip()
    icon = parse_project_icon(request.form.get("icon", ""))

    if not name:
        flash("Название проекта не может быть пустым.")
        return redirect(url_for("main.index", view=request.args.get("view", "inbox"), project_id=project_id))

    duplicate = Project.query.filter(
        Project.user_id == g.user.id,
        db.func.lower(Project.name) == name.lower(),
        Project.id != project.id,
    ).first()
    if duplicate:
        flash("Проект с таким названием уже существует.")
        return redirect(url_for("main.index", view=request.args.get("view", "inbox"), project_id=project_id))

    project.name = name
    project.icon = icon
    db.session.commit()
    flash("Проект обновлен.")
    return redirect(url_for("main.index", view=request.args.get("view", "inbox"), project_id=project_id))


@bp.route("/projects/delete/<int:project_id>", methods=["POST"])
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
        return redirect(url_for("main.index", view=current_view))
    return redirect(url_for("main.index", view=current_view, project_id=selected_project_raw or None))
