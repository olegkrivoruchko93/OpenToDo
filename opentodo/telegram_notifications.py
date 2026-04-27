import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app

from .constants import PROJECT_ICON_MAP
from .models import Task

logger = logging.getLogger(__name__)


def build_task_notification_text(task: Task) -> str:
    """Build the Telegram message body for a due task reminder."""
    parts = ["🔔 Напоминание о задаче", f"✅ Задача: {task.title}"]
    if task.due_at:
        parts.append(f"🕒 Время: {task.due_at.strftime('%d.%m.%Y %H:%M')}")
    if task.project:
        project_icon = PROJECT_ICON_MAP.get(task.project.icon, PROJECT_ICON_MAP["folder"])
        parts.append(f"{project_icon} Проект: {task.project.name}")
    if task.description:
        parts.append(f"📝 Описание: {task.description[:500]}")
    return "\n".join(parts)


def send_task_notification(task: Task) -> bool:
    """Send a task reminder through Telegram and report success."""
    token = task.owner.telegram_bot_token if task.owner else None
    if not token:
        token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = task.owner.telegram_chat_id if task.owner else None
    if not token or not chat_id:
        return False

    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": build_task_notification_text(task),
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
            return bool(body.get("ok"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        logger.warning("Failed to send Telegram task notification for task %s: %s", task.id, error)
        return False
