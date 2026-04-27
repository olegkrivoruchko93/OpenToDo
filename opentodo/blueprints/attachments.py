import io

from flask import Blueprint, flash, g, send_file

from ..auth_utils import login_required
from ..extensions import db
from ..models import Task, TaskAttachment
from ..navigation import redirect_to_current_view


bp = Blueprint("attachments", __name__)


@bp.route("/attachments/<int:attachment_id>/download", methods=["GET"])
@login_required
def download_attachment(attachment_id: int):
    """Send an attachment file owned by the current user."""
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


@bp.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id: int):
    """Delete an attachment owned by the current user."""
    attachment = (
        TaskAttachment.query.join(Task, TaskAttachment.task_id == Task.id)
        .filter(TaskAttachment.id == attachment_id, Task.user_id == g.user.id)
        .first_or_404()
    )
    db.session.delete(attachment)
    db.session.commit()
    flash("Вложение удалено.")
    return redirect_to_current_view()
