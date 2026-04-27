from opentodo.extensions import db
from opentodo.models import Project, Tag, Task, User


def _login(client, user_id: int) -> None:
    with client.session_transaction() as client_session:
        client_session["user_id"] = user_id


def _seed_search_data():
    user = User(username="oleg")
    user.set_password("secret")
    other_user = User(username="alice")
    other_user.set_password("secret")
    db.session.add_all([user, other_user])
    db.session.flush()

    work_project = Project(name="Work Alpha", icon="work", user_id=user.id)
    home_project = Project(name="Home Beta", icon="home", user_id=user.id)
    other_project = Project(name="Work Alpha", icon="work", user_id=other_user.id)
    urgent_tag = Tag(name="Urgent", user_id=user.id)
    urgent_extra_tag = Tag(name="Urgent Followup", user_id=user.id)
    errands_tag = Tag(name="Errands", user_id=user.id)
    db.session.add_all([work_project, home_project, other_project, urgent_tag, urgent_extra_tag, errands_tag])
    db.session.flush()

    release_task = Task(
        title="Write release notes",
        description="Prepare changelog",
        user_id=user.id,
        project_id=work_project.id,
    )
    release_task.tags = [urgent_tag, urgent_extra_tag]
    grocery_task = Task(
        title="Buy milk",
        description="Grocery list",
        user_id=user.id,
        project_id=home_project.id,
    )
    grocery_task.tags = [errands_tag]
    plain_task = Task(title="Plain task", description="No metadata match", user_id=user.id)
    other_task = Task(
        title="Hidden release task",
        description="Should not leak",
        user_id=other_user.id,
        project_id=other_project.id,
    )
    db.session.add_all([release_task, grocery_task, plain_task, other_task])
    db.session.commit()

    return {
        "user": user,
        "work_project": work_project,
        "home_project": home_project,
        "release_task": release_task,
        "grocery_task": grocery_task,
        "plain_task": plain_task,
    }


def test_search_finds_task_by_title(client, app):
    with app.app_context():
        data = _seed_search_data()
        user_id = data["user"].id

    _login(client, user_id)
    response = client.get("/?q=release")

    assert response.status_code == 200
    assert b"Write release notes" in response.data
    assert b"Buy milk" not in response.data
    assert b"Hidden release task" not in response.data


def test_search_finds_task_by_description_case_insensitive(client, app):
    with app.app_context():
        data = _seed_search_data()
        user_id = data["user"].id

    _login(client, user_id)
    response = client.get("/?q=GROCERY")

    assert response.status_code == 200
    assert b"Buy milk" in response.data
    assert b"Write release notes" not in response.data


def test_search_finds_task_by_project_name(client, app):
    with app.app_context():
        data = _seed_search_data()
        user_id = data["user"].id

    _login(client, user_id)
    response = client.get("/?q=work%20alpha")

    assert response.status_code == 200
    assert b"Write release notes" in response.data
    assert b"Buy milk" not in response.data


def test_search_finds_task_by_tag_name_without_duplicates(client, app):
    with app.app_context():
        data = _seed_search_data()
        user_id = data["user"].id

    _login(client, user_id)
    response = client.get("/?q=urgent")

    assert response.status_code == 200
    assert b"Write release notes" in response.data
    assert response.data.count(b'class="task-item') == 1


def test_search_combines_with_project_filter(client, app):
    with app.app_context():
        data = _seed_search_data()
        user_id = data["user"].id
        home_project_id = data["home_project"].id

    _login(client, user_id)
    response = client.get(f"/?q=release&project_id={home_project_id}")

    assert response.status_code == 200
    assert b"Write release notes" not in response.data
    assert b"Buy milk" not in response.data
    assert response.data.count(b'class="task-item') == 0


def test_index_stores_search_query_for_navigation(client, app):
    with app.app_context():
        data = _seed_search_data()
        user_id = data["user"].id

    _login(client, user_id)
    response = client.get("/?q=release")

    assert response.status_code == 200
    with client.session_transaction() as client_session:
        assert client_session["last_search_query"] == "release"
