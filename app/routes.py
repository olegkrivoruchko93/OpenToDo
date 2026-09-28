from flask import render_template, redirect, url_for, request, flash, jsonify, abort
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta

from app.models import db

from app.models.models import User, Task, TaskStatus, Project
from app import app, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


def get_owned_task(task_id):
    """Fetch a task that belongs to the current user, or 404.

    Looking a row up by its raw id would let any signed-in user read or
    change somebody else's tasks, so the owner is always part of the check.
    """
    task = db.session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        abort(404)
    return task


def get_owned_project(project_id):
    """Fetch a project that belongs to the current user, or 404."""
    project = db.session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        abort(404)
    return project


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")

    username = request.form["username"].strip()
    if not username or not request.form["password"]:
        flash('Login and password are required', 'error')
        return redirect(url_for('register'))

    if User.query.filter_by(username=username).first():
        flash('User with this login already exists', 'error')
        return redirect(url_for('register'))

    new_user = User(username=username)
    new_user.set_password(request.form["password"])
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return redirect(url_for('index'))


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user)
        return redirect(url_for('index'))

    flash('Invalid credentials. Please try again.', 'error')
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/")
@login_required
def index():
    date_filter = request.args.get("date_filter")
    filters = [Task.user_id == current_user.id]

    status_filter = request.args.get("status")
    if status_filter:
        try:
            filters.append(Task.status == TaskStatus(status_filter))
        except ValueError:
            pass  # Unknown status in the URL, ignore the filter

    now = datetime.now()

    if date_filter == "today":
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        filters.append(Task.due_date >= start_of_today)
        filters.append(Task.due_date < start_of_today + timedelta(days=1))
    elif date_filter == "upcoming":
        filters.append(Task.due_date >= now)
        filters.append(Task.due_date <= now + timedelta(days=2))

    tasks = Task.query.filter(*filters).options(db.joinedload(Task.project)).all()
    return render_template(
        "index.html",
        tasks=tasks,
        current_date_filter=date_filter or "inbox",
        projects=current_user.projects
    )


@app.route("/add", methods=['POST'])
@login_required
def add():
    title = (request.form.get("title") or "").strip()
    if not title:
        abort(400, description="Title cannot be empty")

    db.session.add(Task(title=title, user_id=current_user.id, status=TaskStatus.TODO))
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/tasks/<task_id>", methods=["GET", "PATCH"])
@login_required
def task(task_id):
    task = get_owned_task(task_id)

    if request.method == "GET":
        return jsonify(task.to_dict()), 200

    data = request.get_json(silent=True)
    if data is None:
        abort(400, description="Invalid request body")
    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            abort(400, description="Title cannot be empty")
        task.title = title
    if "description" in data:
        task.description = data["description"] or None
    if "status" in data:
        try:
            task.status = TaskStatus(data["status"])
        except ValueError:
            abort(400, description="Invalid status value")
    if "due_date" in data:
        if data["due_date"]:
            try:
                task.due_date = datetime.fromisoformat(data["due_date"])
            except (TypeError, ValueError):
                abort(400, description="Invalid due date value")
        else:
            task.due_date = None
    if "project_id" in data:
        project_id = data["project_id"] or None
        if project_id:
            get_owned_project(project_id)  # 404 unless it is the user's own project
        task.project_id = project_id
    if "completed" in data:
        task.completed = bool(data["completed"])

    db.session.commit()
    return jsonify(task.to_dict()), 200


@app.route("/cheked/<task_id>", methods=['PATCH'])
@login_required
def cheked(task_id):
    task = get_owned_task(task_id)
    task.completed = not task.completed
    db.session.commit()
    return jsonify(task.completed), 200


@app.route("/delete/<task_id>", methods=['POST'])
@login_required
def delete(task_id):
    db.session.delete(get_owned_task(task_id))
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/projects", methods=['POST'])
@login_required
def projects():
    db.session.add(Project(user_id=current_user.id, title="New Project"))
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/projects/<project_id>", methods=["PATCH"])
@login_required
def update_project(project_id):
    project = get_owned_project(project_id)

    data = request.get_json(silent=True)
    if data is None:
        abort(400, description="Invalid request body")
    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            abort(400, description="Title cannot be empty")
        project.title = title

    db.session.commit()
    return jsonify(project.to_dict()), 200
