from flask import Blueprint, flash, g, request

from ..auth_utils import login_required
from ..extensions import db
from ..models import Tag
from ..navigation import redirect_to_current_view
from ..parsing import parse_tag_color


bp = Blueprint("tags", __name__)


@bp.route("/tags/add", methods=["POST"])
@login_required
def add_tag():
    """Create a tag for the current user."""
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


@bp.route("/tags/edit/<int:tag_id>", methods=["POST"])
@login_required
def edit_tag(tag_id: int):
    """Update a tag owned by the current user."""
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


@bp.route("/tags/delete/<int:tag_id>", methods=["POST"])
@login_required
def delete_tag(tag_id: int):
    """Delete a tag and detach it from tasks."""
    tag = Tag.query.filter_by(id=tag_id, user_id=g.user.id).first_or_404()
    tag.tasks.clear()
    db.session.delete(tag)
    db.session.commit()
    flash("Метка удалена.")
    return redirect_to_current_view()
