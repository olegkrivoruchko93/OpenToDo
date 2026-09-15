
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, event, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import uuid

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
# initialize the app with the extension
db.init_app(app)

class User(Base):
    __tablename__ = 'user'
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    email_address: Mapped[str] = mapped_column(String, nullable=False)
    tasks = db.relationship('Task', back_populates='user')

@event.listens_for(User, "before_insert")
def generate_user_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())

class Task(Base):
    __tablename__ = 'task'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey('user.id'), nullable=False)
    user: Mapped["User"] = db.relationship(back_populates='tasks')

@app.route("/register", methods=['GET', 'POST'])
def register():
    return "registerin na?"

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)