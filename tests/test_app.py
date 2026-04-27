from datetime import datetime

import pytest
from flask import session, url_for

from opentodo.backup import apply_json_backup, build_backup_csv_zip, collect_backup_payload, parse_csv_zip_to_payload
from opentodo.constants import CSRF_SESSION_KEY
from opentodo.csrf import get_csrf_token
from opentodo.extensions import db
from opentodo.models import ChecklistItem, Task, User
from opentodo.recurrence import calculate_next_due_at
from opentodo.task_utils import serialize_task


def _login_with_csrf(client, user_id: int) -> str:
    csrf_token = "test-csrf-token"
    with client.session_transaction() as client_session:
        client_session["user_id"] = user_id
        client_session[CSRF_SESSION_KEY] = csrf_token
    return csrf_token


def test_create_app_registers_routes(app):
    route_names = {rule.endpoint for rule in app.url_map.iter_rules()}

    assert "main.index" in route_names
    assert "auth.login" in route_names
    assert "auth.register" in route_names


def test_index_redirects_anonymous_user_to_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_csrf_token_is_created_once(app):
    with app.test_request_context("/"):
        first_token = get_csrf_token()
        second_token = get_csrf_token()

        assert first_token
        assert second_token == first_token
        assert session[CSRF_SESSION_KEY] == first_token


def test_user_password_hashing(app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")

        db.session.add(user)
        db.session.commit()

        saved_user = User.query.filter_by(username="oleg").one()
        assert saved_user.check_password("secret") is True
        assert saved_user.check_password("wrong") is False
        assert saved_user.password_hash != "secret"


def test_login_page_is_available(client):
    response = client.get("/login")

    assert response.status_code == 200


def test_url_for_index_works_inside_app_context(app):
    with app.test_request_context("/"):
        assert url_for("main.index") == "/"


def test_task_priority_defaults_to_medium(app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()

        task = Task(title="Default priority", description="", user_id=user.id)
        db.session.add(task)
        db.session.commit()

        assert task.priority == "medium"


def test_add_task_saves_priority_and_renders_priority_class(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(
        "/add",
        data={
            "csrf_token": csrf_token,
            "title": "Urgent task",
            "description": "",
            "priority": "high",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        task = Task.query.filter_by(title="Urgent task", user_id=user_id).one()
        assert task.priority == "high"

    response = client.get("/")
    assert response.status_code == 200
    assert b"task-priority-high" in response.data
    assert b"Urgent task" in response.data


def test_add_task_saves_recurrence(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(
        "/add",
        data={
            "csrf_token": csrf_token,
            "title": "Weekly task",
            "description": "",
            "due_at": "2026-04-27T09:00",
            "recurrence": "weekly",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        task = Task.query.filter_by(title="Weekly task", user_id=user_id).one()
        assert task.recurrence == "weekly"


def test_add_recurring_task_requires_due_at(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(
        "/add",
        data={
            "csrf_token": csrf_token,
            "title": "No due date",
            "description": "",
            "recurrence": "daily",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        assert Task.query.filter_by(title="No due date", user_id=user_id).count() == 0


@pytest.mark.parametrize(
    ("recurrence", "due_at", "expected_due_at"),
    [
        ("daily", datetime(2026, 4, 27, 9, 0), datetime(2026, 4, 28, 9, 0)),
        ("weekly", datetime(2026, 4, 27, 9, 0), datetime(2026, 5, 4, 9, 0)),
        ("monthly", datetime(2026, 1, 31, 9, 0), datetime(2026, 2, 28, 9, 0)),
        ("yearly", datetime(2024, 2, 29, 9, 0), datetime(2025, 2, 28, 9, 0)),
    ],
)
def test_calculate_next_due_at(recurrence, due_at, expected_due_at):
    assert calculate_next_due_at(due_at, recurrence) == expected_due_at


def test_completing_recurring_task_creates_next_instance(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(
            title="Pay rent",
            description="Transfer money",
            due_at=datetime(2026, 1, 31, 9, 0),
            due_date=datetime(2026, 1, 31, 9, 0).date(),
            recurrence="monthly",
            priority="high",
            user_id=user.id,
        )
        db.session.add(task)
        db.session.flush()
        db.session.add(ChecklistItem(task_id=task.id, title="Open bank app", is_done=True))
        db.session.commit()
        user_id = user.id
        task_id = task.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(f"/toggle/{task_id}", data={"csrf_token": csrf_token})

    assert response.status_code == 302
    with app.app_context():
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.id.asc()).all()
        assert len(tasks) == 2
        completed_task, next_task = tasks
        assert completed_task.is_done is True
        assert completed_task.is_archived is True
        assert completed_task.is_deleted is False
        assert next_task.is_done is False
        assert next_task.is_archived is False
        assert next_task.is_deleted is False
        assert next_task.recurrence == "monthly"
        assert next_task.recurrence_parent_id == completed_task.id
        assert next_task.due_at == datetime(2026, 2, 28, 9, 0)
        assert next_task.priority == "high"
        assert next_task.description == "Transfer money"
        assert len(next_task.checklist_items) == 1
        assert next_task.checklist_items[0].title == "Open bank app"
        assert next_task.checklist_items[0].is_done is False


def test_completing_one_off_task_does_not_create_next_instance(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(title="One-off", description="", user_id=user.id)
        db.session.add(task)
        db.session.commit()
        user_id = user.id
        task_id = task.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(f"/toggle/{task_id}", data={"csrf_token": csrf_token})

    assert response.status_code == 302
    with app.app_context():
        tasks = Task.query.filter_by(user_id=user_id).all()
        assert len(tasks) == 1
        assert tasks[0].is_done is True
        assert tasks[0].is_archived is True
        assert tasks[0].is_deleted is False


def test_completing_task_moves_it_from_inbox_to_archive(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(title="Archive me", description="", user_id=user.id)
        db.session.add(task)
        db.session.commit()
        user_id = user.id
        task_id = task.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(f"/toggle/{task_id}", data={"csrf_token": csrf_token, "view": "inbox"})

    assert response.status_code == 302
    with app.app_context():
        archived_task = Task.query.filter_by(id=task_id, user_id=user_id).one()
        assert archived_task.is_done is True
        assert archived_task.is_archived is True
        assert archived_task.is_deleted is False

    inbox_response = client.get("/")
    archive_response = client.get("/?view=archive")

    assert b"Archive me" not in inbox_response.data
    assert b"Archive me" in archive_response.data


def test_deleting_task_moves_it_to_trash(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(title="Trash me", description="", user_id=user.id)
        db.session.add(task)
        db.session.commit()
        user_id = user.id
        task_id = task.id

    csrf_token = _login_with_csrf(client, user_id)
    response = client.post(f"/delete/{task_id}", data={"csrf_token": csrf_token, "view": "inbox"})

    assert response.status_code == 302
    with app.app_context():
        deleted_task = Task.query.filter_by(id=task_id, user_id=user_id).one()
        assert deleted_task.is_deleted is True
        assert deleted_task.is_archived is False

    inbox_response = client.get("/")
    trash_response = client.get("/?view=trash")

    assert b"Trash me" not in inbox_response.data
    assert b"Trash me" in trash_response.data


def test_trash_excludes_archived_tasks(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        archived_task = Task(
            title="Archived only",
            description="",
            is_done=True,
            is_archived=True,
            user_id=user.id,
        )
        deleted_task = Task(title="Deleted only", description="", is_deleted=True, user_id=user.id)
        db.session.add_all([archived_task, deleted_task])
        db.session.commit()
        user_id = user.id

    _login_with_csrf(client, user_id)
    trash_response = client.get("/?view=trash")
    archive_response = client.get("/?view=archive")

    assert b"Deleted only" in trash_response.data
    assert b"Archived only" not in trash_response.data
    assert b"Archived only" in archive_response.data
    assert b"Deleted only" not in archive_response.data


def test_index_shows_checklist_indicator_for_tasks_with_items(client, app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(title="Task with checklist", description="", user_id=user.id)
        db.session.add(task)
        db.session.flush()
        db.session.add(ChecklistItem(task_id=task.id, title="First item"))
        db.session.commit()
        user_id = user.id

    _login_with_csrf(client, user_id)
    response = client.get("/")

    assert response.status_code == 200
    assert b"task-checklist-indicator" in response.data
    assert "Чек-лист: 1".encode() in response.data


def test_serialize_task_includes_priority(app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(title="Low priority", description="", priority="low", user_id=user.id)
        db.session.add(task)
        db.session.commit()

        payload = serialize_task(task)

    assert payload["priority"] == "low"
    assert payload["priority_label"] == "Низкий"


def test_serialize_task_includes_recurrence(app):
    with app.app_context():
        user = User(username="oleg")
        user.set_password("secret")
        db.session.add(user)
        db.session.flush()
        task = Task(title="Recurring", description="", recurrence="daily", user_id=user.id)
        db.session.add(task)
        db.session.commit()

        payload = serialize_task(task)

    assert payload["recurrence"] == "daily"
    assert payload["recurrence_label"] == "Каждый день"


def test_backup_roundtrip_preserves_task_priority(app):
    with app.app_context():
        source_user = User(username="oleg")
        source_user.set_password("secret")
        target_user = User(username="alice")
        target_user.set_password("secret")
        db.session.add_all([source_user, target_user])
        db.session.flush()
        db.session.add(Task(title="Backup task", description="", priority="high", user_id=source_user.id))
        db.session.commit()
        source_user_id = source_user.id
        target_user_id = target_user.id

        payload = collect_backup_payload(source_user_id)
        assert payload["tasks"][0]["priority"] == "high"

        parsed_payload = parse_csv_zip_to_payload(build_backup_csv_zip(payload))
        assert parsed_payload["tasks"][0]["priority"] == "high"

        stats = apply_json_backup(parsed_payload, target_user_id, mode="merge")
        db.session.commit()

        imported_task = Task.query.filter_by(user_id=target_user_id, title="Backup task").one()
        assert stats["tasks"] == 1
        assert imported_task.priority == "high"


def test_backup_roundtrip_preserves_task_recurrence(app):
    with app.app_context():
        source_user = User(username="oleg")
        source_user.set_password("secret")
        target_user = User(username="alice")
        target_user.set_password("secret")
        db.session.add_all([source_user, target_user])
        db.session.flush()
        db.session.add(
            Task(
                title="Backup recurring task",
                description="",
                due_at=datetime(2026, 4, 27, 9, 0),
                due_date=datetime(2026, 4, 27).date(),
                recurrence="weekly",
                user_id=source_user.id,
            )
        )
        db.session.commit()
        source_user_id = source_user.id
        target_user_id = target_user.id

        payload = collect_backup_payload(source_user_id)
        assert payload["tasks"][0]["recurrence"] == "weekly"

        parsed_payload = parse_csv_zip_to_payload(build_backup_csv_zip(payload))
        assert parsed_payload["tasks"][0]["recurrence"] == "weekly"

        stats = apply_json_backup(parsed_payload, target_user_id, mode="merge")
        db.session.commit()

        imported_task = Task.query.filter_by(user_id=target_user_id, title="Backup recurring task").one()
        assert stats["tasks"] == 1
        assert imported_task.recurrence == "weekly"


def test_backup_roundtrip_preserves_task_archive_and_trash_state(app):
    with app.app_context():
        source_user = User(username="oleg")
        source_user.set_password("secret")
        target_user = User(username="alice")
        target_user.set_password("secret")
        db.session.add_all([source_user, target_user])
        db.session.flush()
        db.session.add_all(
            [
                Task(
                    title="Archived backup task",
                    description="",
                    is_done=True,
                    is_archived=True,
                    user_id=source_user.id,
                ),
                Task(
                    title="Deleted backup task",
                    description="",
                    is_deleted=True,
                    user_id=source_user.id,
                ),
            ]
        )
        db.session.commit()
        source_user_id = source_user.id
        target_user_id = target_user.id

        payload = collect_backup_payload(source_user_id)
        tasks_by_title = {task["title"]: task for task in payload["tasks"]}
        assert tasks_by_title["Archived backup task"]["is_archived"] is True
        assert tasks_by_title["Deleted backup task"]["is_deleted"] is True

        parsed_payload = parse_csv_zip_to_payload(build_backup_csv_zip(payload))
        parsed_tasks_by_title = {task["title"]: task for task in parsed_payload["tasks"]}
        assert parsed_tasks_by_title["Archived backup task"]["is_archived"] is True
        assert parsed_tasks_by_title["Deleted backup task"]["is_deleted"] is True

        stats = apply_json_backup(parsed_payload, target_user_id, mode="merge")
        db.session.commit()

        imported_archived_task = Task.query.filter_by(
            user_id=target_user_id,
            title="Archived backup task",
        ).one()
        imported_deleted_task = Task.query.filter_by(
            user_id=target_user_id,
            title="Deleted backup task",
        ).one()
        assert stats["tasks"] == 2
        assert imported_archived_task.is_done is True
        assert imported_archived_task.is_archived is True
        assert imported_archived_task.is_deleted is False
        assert imported_deleted_task.is_archived is False
        assert imported_deleted_task.is_deleted is True
