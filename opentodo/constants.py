PROJECT_ICON_OPTIONS = [
    ("folder", "📁 Папка"),
    ("work", "💼 Работа"),
    ("study", "📚 Учеба"),
    ("health", "💪 Здоровье"),
    ("home", "🏠 Дом"),
    ("idea", "💡 Идеи"),
    ("finance", "💰 Финансы"),
    ("travel", "✈️ Путешествия"),
]
PROJECT_ICON_MAP = {key: label.split(" ", 1)[0] for key, label in PROJECT_ICON_OPTIONS}
DEFAULT_PROJECT_ICON = "folder"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_TASK = 5
ATTACHMENT_FIELD_NAME = "attachments[]"
CSRF_SESSION_KEY = "_csrf_token"
CSRF_FIELD_NAME = "csrf_token"
