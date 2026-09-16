from flask import Flask, render_template, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, event, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# DB models
class User(db.Model):
    __tablename__ = 'user'
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(150), nullable=False)
    tasks = db.relationship('Task', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    __tablename__ = 'task'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey('user.id'), nullable=False)
    user: Mapped["User"] = db.relationship(back_populates='tasks')

# Objects events
@event.listens_for(User, "before_insert")
def generate_user_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())

# Objects events
@event.listens_for(Task, "before_insert")
def generate_task_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())

# Routes
@app.route("/register", methods=['GET', 'POST'])
def register():

    if request.method == 'POST':    
        # Collect info from from
        username = request.form["username"]
        password = request.form["password"]
        # Check if its in the db
        user = User.query.filter_by(username=username).first()
        if not user: # Already exist
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            session['username'] = username
        return redirect(url_for('index'))
    elif request.method == 'GET':
        return render_template("auth.html")

@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method == 'POST':    
        # Collect info from from
        username = request.form["username"]
        password = request.form["password"]
        # Check if its in the db
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return render_template("auth.html")
    elif request.method == 'GET':
        return render_template("auth.html")
 
@app.route("/")
def index():
    if "username" in session:
        return render_template("home.html", username=session["username"])
    return redirect(url_for('login'))

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)