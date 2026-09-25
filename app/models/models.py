from flask_login import UserMixin
from sqlalchemy import String, event, ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from enum import Enum as PyEnum

from app.models import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(150), nullable=False)
    tasks = db.relationship('Task', back_populates='user')
    projects = db.relationship('Projects', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TaskStatus(PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(db.Model):
    __tablename__ = 'task'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    due_date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), nullable=False, default=TaskStatus.TODO
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey('user.id'), nullable=False)
    user: Mapped["User"] = db.relationship('User', back_populates='tasks')
    project_id: Mapped[str] = mapped_column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": str(self.status.value),
            "due_date": str(self.due_date),
            "project_id": self.project_id
        }

class Projects(db.Model):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey('user.id'), nullable=False)
    user: Mapped["User"] = db.relationship('User', back_populates='projects')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
        }

@event.listens_for(User, "before_insert")
def generate_user_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())


@event.listens_for(Task, "before_insert")
def generate_task_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())

@event.listens_for(Projects, "before_insert")
def generate_project_id(mapper, connection, target):
    if not target.id:
        target.id = str(uuid.uuid4())
