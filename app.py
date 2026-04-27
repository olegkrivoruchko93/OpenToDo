import os

from opentodo import create_app
from opentodo.background_jobs import start_notification_scheduler
from opentodo.db_init import init_db


app = create_app()
init_db(app)
start_notification_scheduler(app)


if __name__ == "__main__":
    app.run(host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"), debug=True)
