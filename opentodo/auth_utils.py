from functools import wraps

from flask import g, redirect, session, url_for

from .extensions import db
from .models import User


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None
