from flask import g

from .csrf import get_csrf_token
from .parsing import parse_tag_color


def inject_current_user():
    """Expose user, CSRF, and tag color helpers to templates."""
    return {"current_user": g.user, "csrf_token": get_csrf_token, "tag_color": parse_tag_color}
