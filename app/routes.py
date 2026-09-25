from flask import render_template, session, redirect, url_for, request, flash, jsonify, abort, Blueprint
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy.orm import joinedload

from app.models import db

from app.models.models import User, Task, TaskStatus, Projects
from app import app, login_manager
from datetime import datetime, timedelta


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route("/register", methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user:
            flash('User with this login already exists', 'error')
            return redirect(url_for('register'))
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            session['username'] = username
            return redirect(url_for('index'))
    elif request.method == 'GET':
        return render_template("register.html")

@app.route("/tasks/<task_id>", methods=["GET", "PATCH"])
@login_required
def task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)
    if request.method == "PATCH":
        data = request.get_json()
        if not data:
            abort(400, description="Invalid request body")
        if "title" in data:
            if not data["title"] or len(data["title"]) == 0:
                abort(400, description="Title cannot be empty")
            task.title = data["title"]
        if "description" in data:
            task.description = data["description"]
        if "status" in data:
            try:
                task.status = TaskStatus(data["status"])
            except ValueError:
                abort(400, description="Invalid status value")
        if "due_date" in data:
            task.due_date = datetime.fromisoformat(data["due_date"])
        if "project_id" in data:
            task.project_id = data["project_id"]
        db.session.commit()
        return jsonify(task.to_dict()), 200
    return jsonify(task.to_dict()), 200



@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method == 'POST':    
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return render_template("login.html")
    elif request.method == 'GET':
        return render_template("login.html")

@app.route("/")
@login_required
def index():

    status_filter = request.args.get("status")
    date_filter = request.args.get("date_filter")

    filters = [Task.user_id == current_user.id]

    try:
        if status_filter:
            filters.append(Task.status == TaskStatus(status_filter))
    except ValueError:
        pass  # Invalid status filter, ignore it
 

    now = datetime.now()

    if date_filter == "today":
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=0)
        filters.append(Task.due_date >= start_of_today)
        filters.append(Task.due_date <= end_of_today)
    elif date_filter == "upcoming":
        upcoming_end = now + timedelta(days=2)
        filters.append(Task.due_date >= now)
        filters.append(Task.due_date <= upcoming_end)

    tasks_query = Task.query.filter(*filters)
    tasks = tasks_query.options(db.joinedload(Task.project)).all()
    projects = current_user.projects
    return render_template(
        "index.html",
        tasks=tasks,
        current_filter=status_filter or "all",
        current_date_filter=date_filter or "all",
        projects=projects
    )

@app.route("/add", methods=['POST'])
@login_required
def add():
    title = request.form["task-title"]
    if len(title) > 0:
        new_task = Task(title=title, user_id=current_user.id, status=TaskStatus.TODO)
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('index'))

@app.route("/delete/<task_id>", methods=['POST'])
@login_required
def delete(task_id):
    task = db.session.get(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))

@app.route("/projects/<project_id>", methods=["PATCH"])
@login_required
def update_project(project_id):
    project = db.session.get(Projects, project_id)
    if not project:
        abort(404)
    data = request.get_json()
    if not data:
        abort(400, description="Invalid request body")
    if "title" in data:
        if not data["title"] or len(data["title"]) == 0:
            abort(400, description="Title cannot be empty")
        project.title = data["title"]
    db.session.commit()
    return jsonify(project.to_dict()), 200


@app.route("/projects", methods=['POST'])
@login_required
def projects():
    if request.method == 'POST':
        new_project = Projects(user_id=current_user.id)
        new_project.title = "New Project"
        db.session.add(new_project)
        db.session.commit()
        status_filter = request.args.get("status")
        try:
            if status_filter:
                TaskStatus(status_filter)
            else:
                status_filter = None
        except ValueError:
            status_filter = None
        if status_filter:
            tasks = [t for t in current_user.tasks if t.status == TaskStatus(status_filter)]
        else:
            tasks = current_user.tasks
        projects = current_user.projects
        return render_template(
                "index.html",
                username=current_user.username,
                tasks=tasks,
                current_filter=status_filter or "all",
                projects=projects
            )
    elif request.method == 'GET':
        pass

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))