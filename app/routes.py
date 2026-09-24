from flask import render_template, session, redirect, url_for, request, flash, jsonify, abort, Blueprint
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from app.models import db

from app.models.models import User, Task, TaskStatus
from app import app, login_manager


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
def taskk(task_id):
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
    return render_template(
        "index.html",
        username=current_user.username,
        tasks=tasks,
        current_filter=status_filter or "all",
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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))