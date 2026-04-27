import hmac
from secrets import token_urlsafe

from flask import abort, jsonify, request, session

from .constants import CSRF_FIELD_NAME, CSRF_SESSION_KEY


def get_csrf_token() -> str:
    """Return the session CSRF token, creating one when needed."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def is_valid_csrf_token() -> bool:
    """Check whether the submitted CSRF token matches the session token."""
    expected_token = session.get(CSRF_SESSION_KEY)
    supplied_token = (
        request.form.get(CSRF_FIELD_NAME)
        or request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
    )
    return bool(
        expected_token
        and supplied_token
        and hmac.compare_digest(str(expected_token), str(supplied_token))
    )


def validate_csrf_for_mutations():
    """Reject POST requests that do not include a valid CSRF token."""
    if request.method != "POST":
        return None
    if is_valid_csrf_token():
        return None
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": False, "error": "Недействительный CSRF-токен."}), 403
    abort(403)
