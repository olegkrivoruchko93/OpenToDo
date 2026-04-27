from urllib.parse import urlparse

from flask import redirect, request, url_for


def get_navigation_context():
    # Prefer explicit form fields from POST, fallback to query string.
    current_view = (request.form.get("view") or request.args.get("view") or "inbox").strip()
    if current_view not in {"inbox", "today", "plans", "trash"}:
        current_view = "inbox"
    selected_project_raw = (
        request.form.get("filter_project_id")
        or request.form.get("project_id")
        or request.args.get("project_id")
        or ""
    ).strip()
    if not selected_project_raw.isdigit():
        selected_project_raw = ""
    selected_tag_raw = (request.form.get("tag_id") or request.args.get("tag_id") or "").strip()
    if not selected_tag_raw.isdigit():
        selected_tag_raw = ""
    return current_view, selected_project_raw, selected_tag_raw


def redirect_to_current_view():
    referrer = (request.referrer or "").strip()
    if referrer:
        parsed_referrer = urlparse(referrer)
        current_host = request.host.split(":", 1)[0]
        if parsed_referrer.scheme in {"http", "https"} and parsed_referrer.hostname == current_host:
            return redirect(referrer)

    current_view, selected_project_raw, selected_tag_raw = get_navigation_context()
    return redirect(
        url_for("main.index", view=current_view, project_id=selected_project_raw or None, tag_id=selected_tag_raw or None)
    )
