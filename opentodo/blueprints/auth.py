from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..auth_utils import login_required
from ..extensions import db
from ..models import User


bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account or show the registration form."""
    if g.user is not None:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Введите логин и пароль.")
        elif User.query.filter_by(username=username).first():
            flash("Пользователь с таким логином уже существует.")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Регистрация успешна. Теперь войдите в аккаунт.")
            return redirect(url_for("auth.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a user and start a new session."""
    if g.user is not None:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Неверный логин или пароль.")
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("main.index"))

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Clear the current session and redirect to login."""
    session.clear()
    return redirect(url_for("auth.login"))
