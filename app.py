from flask import Flask, render_template, session, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, event, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'          # redirect here if not logged in
login_manager.login_message = 'You must be authorized'

db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(150), nullable=False)
    tasks = db.relationship('Task', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

class Task(db.Model):
    __tablename__ = 'task'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey('user.id'), nullable=False)
    user: Mapped["User"] = db.relationship(back_populates='tasks')

@event.listens_for(User, "before_insert")
def generate_user_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())

@event.listens_for(Task, "before_insert")
def generate_task_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())

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
    

@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method == 'POST':    
        # Collect info from from
        username = request.form["username"]
        password = request.form["password"]
        # Check if its in the db
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
    return render_template("index.html", username=current_user.username, tasks=current_user.tasks)

@app.route("/add", methods=['POST'])
@login_required
def add():
    description = request.form["task-description"]
    if len(description) > 0:
        new_task = Task(description=description, user_id=current_user.id)
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
