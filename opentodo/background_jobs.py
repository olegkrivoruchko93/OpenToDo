import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from .extensions import db
from .models import Task, User
from .telegram_notifications import send_task_notification

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def send_due_task_notifications(app) -> None:
    with app.app_context():
        now = datetime.now()
        tasks = (
            Task.query.join(User, Task.user_id == User.id)
            .filter(
                Task.is_done.is_(False),
                Task.due_at.isnot(None),
                Task.due_at <= now,
                Task.notification_sent_at.is_(None),
                Task.telegram_notification_enabled.is_(True),
                User.telegram_notifications_enabled.is_(True),
                User.telegram_bot_token.isnot(None),
                User.telegram_chat_id.isnot(None),
            )
            .order_by(Task.due_at.asc())
            .limit(50)
            .all()
        )
        for task in tasks:
            if send_task_notification(task):
                task.notification_sent_at = now
                db.session.add(task)
                db.session.commit()
            else:
                db.session.rollback()


def start_notification_scheduler(app) -> None:
    global _scheduler
    if _scheduler is not None or not app.config.get("NOTIFICATIONS_ENABLED", True):
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    interval_seconds = max(int(app.config.get("NOTIFICATIONS_POLL_INTERVAL_SECONDS", 60)), 10)
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        send_due_task_notifications,
        "interval",
        args=[app],
        seconds=interval_seconds,
        id="send_due_task_notifications",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
