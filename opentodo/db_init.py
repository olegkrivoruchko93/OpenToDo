from flask import Flask
from sqlalchemy import inspect, text

from .extensions import db


def init_db(app: Flask) -> None:
    """Create database tables and apply lightweight SQLite migrations."""
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if not inspector.has_table("project"):
            db.session.execute(
                text(
                    "CREATE TABLE project ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(120) NOT NULL, "
                    "icon VARCHAR(32) NOT NULL DEFAULT 'folder', "
                    "created_at DATETIME NOT NULL, "
                    "user_id INTEGER NOT NULL)"
                )
            )
            db.session.commit()
        project_columns = {column["name"] for column in inspector.get_columns("project")}
        if "icon" not in project_columns:
            db.session.execute(text("ALTER TABLE project ADD COLUMN icon VARCHAR(32) DEFAULT 'folder'"))
            db.session.execute(text("UPDATE project SET icon = 'folder' WHERE icon IS NULL OR icon = ''"))
            db.session.commit()
        task_columns = {column["name"] for column in inspector.get_columns("task")}
        if "user_id" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN user_id INTEGER"))
            db.session.commit()
        if "description" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN description TEXT DEFAULT ''"))
            db.session.execute(text("UPDATE task SET description = '' WHERE description IS NULL"))
            db.session.commit()
        if "project_id" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN project_id INTEGER"))
            db.session.commit()
        if "due_date" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN due_date DATE"))
            db.session.commit()
        if "due_at" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN due_at DATETIME"))
            db.session.execute(text("UPDATE task SET due_at = due_date || ' 09:00:00' WHERE due_date IS NOT NULL"))
            db.session.commit()
        if "notification_sent_at" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN notification_sent_at DATETIME"))
            db.session.commit()
        if "telegram_notification_enabled" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN telegram_notification_enabled BOOLEAN DEFAULT 1"))
            db.session.execute(
                text("UPDATE task SET telegram_notification_enabled = 1 WHERE telegram_notification_enabled IS NULL")
            )
            db.session.commit()
        if "priority" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN priority VARCHAR(16) DEFAULT 'medium'"))
            db.session.execute(text("UPDATE task SET priority = 'medium' WHERE priority IS NULL OR priority = ''"))
            db.session.commit()
        if "recurrence" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN recurrence VARCHAR(16)"))
            db.session.commit()
        if "recurrence_parent_id" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN recurrence_parent_id INTEGER"))
            db.session.commit()
        if "is_archived" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN is_archived BOOLEAN DEFAULT 0"))
            db.session.execute(text("UPDATE task SET is_archived = 1 WHERE is_done = 1"))
            db.session.execute(text("UPDATE task SET is_archived = 0 WHERE is_archived IS NULL"))
            db.session.commit()
        if "is_deleted" not in task_columns:
            db.session.execute(text("ALTER TABLE task ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
            db.session.execute(text("UPDATE task SET is_deleted = 0 WHERE is_deleted IS NULL"))
            db.session.commit()
        user_columns = {column["name"] for column in inspector.get_columns("user")}
        if "telegram_bot_token" not in user_columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN telegram_bot_token VARCHAR(255)"))
            db.session.commit()
        if "telegram_chat_id" not in user_columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN telegram_chat_id VARCHAR(64)"))
            db.session.commit()
        if "telegram_username" not in user_columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN telegram_username VARCHAR(128)"))
            db.session.commit()
        if "telegram_notifications_enabled" not in user_columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN telegram_notifications_enabled BOOLEAN DEFAULT 0"))
            db.session.execute(
                text(
                    "UPDATE user SET telegram_notifications_enabled = 0 "
                    "WHERE telegram_notifications_enabled IS NULL"
                )
            )
            db.session.commit()
        if not inspector.has_table("checklist_item"):
            db.session.execute(
                text(
                    "CREATE TABLE checklist_item ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "task_id INTEGER NOT NULL, "
                    "title VARCHAR(255) NOT NULL, "
                    "is_done BOOLEAN NOT NULL DEFAULT 0, "
                    "position INTEGER NOT NULL DEFAULT 0)"
                )
            )
            db.session.commit()
        if not inspector.has_table("task_attachment"):
            db.session.execute(
                text(
                    "CREATE TABLE task_attachment ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "task_id INTEGER NOT NULL, "
                    "filename VARCHAR(255) NOT NULL, "
                    "content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream', "
                    "size_bytes INTEGER NOT NULL, "
                    "content BLOB NOT NULL, "
                    "created_at DATETIME NOT NULL)"
                )
            )
            db.session.commit()
        db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_task_attachment_task_id ON task_attachment(task_id)"))
        db.session.commit()
        if not inspector.has_table("tag"):
            db.session.execute(
                text(
                    "CREATE TABLE tag ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(64) NOT NULL, "
                    "color VARCHAR(16) NOT NULL DEFAULT '#5b7cfa', "
                    "created_at DATETIME NOT NULL, "
                    "user_id INTEGER NOT NULL)"
                )
            )
            db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_tag_user_name ON tag(user_id, name)"))
            db.session.commit()
        tag_columns = {column["name"] for column in inspector.get_columns("tag")} if inspector.has_table("tag") else set()
        if inspector.has_table("tag") and "color" not in tag_columns:
            db.session.execute(text("ALTER TABLE tag ADD COLUMN color VARCHAR(16) DEFAULT '#5b7cfa'"))
            db.session.execute(text("UPDATE tag SET color = '#5b7cfa' WHERE color IS NULL OR color = ''"))
            db.session.commit()
        if not inspector.has_table("task_tag"):
            db.session.execute(
                text(
                    "CREATE TABLE task_tag ("
                    "task_id INTEGER NOT NULL, "
                    "tag_id INTEGER NOT NULL, "
                    "PRIMARY KEY (task_id, tag_id))"
                )
            )
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_task_tag_task_id ON task_tag(task_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_task_tag_tag_id ON task_tag(tag_id)"))
            db.session.commit()
