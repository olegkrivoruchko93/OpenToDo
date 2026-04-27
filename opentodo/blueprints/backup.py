import json
from datetime import datetime

from flask import Blueprint, Response, flash, g, request

from ..auth_utils import login_required
from ..backup import apply_json_backup, build_backup_csv_zip, collect_backup_payload, parse_csv_zip_to_payload
from ..extensions import db
from ..navigation import redirect_to_current_view


bp = Blueprint("backup", __name__)


@bp.route("/backup/export/json", methods=["GET", "POST"])
@login_required
def export_backup_json():
    """Download the current user's backup as a JSON file."""
    payload = collect_backup_payload(g.user.id)
    file_name = f"opentodo-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    response = Response(body, mimetype="application/json")
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@bp.route("/backup/export/csv", methods=["GET", "POST"])
@login_required
def export_backup_csv():
    """Download the current user's backup as a ZIP archive of CSV files."""
    payload = collect_backup_payload(g.user.id)
    file_name = f"opentodo-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
    csv_zip = build_backup_csv_zip(payload)
    response = Response(csv_zip, mimetype="application/zip")
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@bp.route("/backup/import/json", methods=["POST"])
@login_required
def import_backup_json():
    """Import the current user's data from an uploaded JSON backup."""
    mode = (request.form.get("mode") or "merge").strip().lower()
    file = request.files.get("backup_file")
    if file is None or not file.filename:
        flash("Выберите JSON файл для импорта.")
        return redirect_to_current_view()
    try:
        payload = json.loads(file.read().decode("utf-8-sig"))
        stats = apply_json_backup(payload, g.user.id, mode)
        db.session.commit()
        flash(
            "Импорт JSON завершен. "
            f"Проекты: {stats['projects']}, метки: {stats['tags']}, задачи: {stats['tasks']}, "
            f"чеклист: {stats['checklist_items']}, вложения: {stats['attachments']}."
        )
    except Exception as error:
        db.session.rollback()
        flash(f"Ошибка импорта JSON: {error}")
    return redirect_to_current_view()


@bp.route("/backup/import/csv", methods=["POST"])
@login_required
def import_backup_csv():
    """Import the current user's data from an uploaded CSV ZIP backup."""
    mode = (request.form.get("mode") or "merge").strip().lower()
    file = request.files.get("backup_file")
    if file is None or not file.filename:
        flash("Выберите ZIP CSV файл для импорта.")
        return redirect_to_current_view()
    try:
        payload = parse_csv_zip_to_payload(file.read())
        stats = apply_json_backup(payload, g.user.id, mode)
        db.session.commit()
        flash(
            "Импорт CSV завершен. "
            f"Проекты: {stats['projects']}, метки: {stats['tags']}, задачи: {stats['tasks']}, "
            f"чеклист: {stats['checklist_items']}, вложения: {stats['attachments']}."
        )
    except Exception as error:
        db.session.rollback()
        flash(f"Ошибка импорта CSV: {error}")
    return redirect_to_current_view()
