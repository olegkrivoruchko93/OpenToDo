PROJECT_ICON_OPTIONS = [
    ("folder", "📁 Папка"),
    ("work", "💼 Работа"),
    ("study", "📚 Учеба"),
    ("health", "💪 Здоровье"),
    ("home", "🏠 Дом"),
    ("idea", "💡 Идеи"),
    ("finance", "💰 Финансы"),
    ("travel", "✈️ Путешествия"),
    ("shopping", "🛒 Покупки"),
    ("food", "🍽️ Еда"),
    ("sport", "🏃 Спорт"),
    ("music", "🎵 Музыка"),
    ("art", "🎨 Творчество"),
    ("reading", "📖 Чтение"),
    ("code", "💻 Код"),
    ("calendar", "📅 Расписание"),
    ("star", "⭐ Важное"),
    ("rocket", "🚀 Запуск"),
    ("target", "🎯 Цели"),
    ("garden", "🌱 Сад"),
    ("pet", "🐾 Питомцы"),
    ("car", "🚗 Авто"),
    ("tools", "🛠️ Ремонт"),
    ("gift", "🎁 Подарки"),
    ("camera", "📷 Фото"),
    ("game", "🎮 Игры"),
    ("heart", "❤️ Личное"),
    ("archive", "🗂️ Архив"),
]
PROJECT_ICON_MAP = {key: label.split(" ", 1)[0] for key, label in PROJECT_ICON_OPTIONS}
DEFAULT_PROJECT_ICON = "folder"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_TASK = 5
ATTACHMENT_FIELD_NAME = "attachments[]"
CSRF_SESSION_KEY = "_csrf_token"
CSRF_FIELD_NAME = "csrf_token"
DEFAULT_TASK_PRIORITY = "medium"
TASK_PRIORITY_OPTIONS = [
    ("high", "Высокий"),
    ("medium", "Средний"),
    ("low", "Низкий"),
]
TASK_PRIORITY_LABELS = dict(TASK_PRIORITY_OPTIONS)
TASK_PRIORITY_VALUES = set(TASK_PRIORITY_LABELS)
TASK_RECURRENCE_OPTIONS = [
    ("", "Не повторять"),
    ("daily", "Каждый день"),
    ("weekly", "Каждую неделю"),
    ("monthly", "Каждый месяц"),
    ("yearly", "Каждый год"),
]
TASK_RECURRENCE_LABELS = dict(TASK_RECURRENCE_OPTIONS)
TASK_RECURRENCE_VALUES = {value for value, _label in TASK_RECURRENCE_OPTIONS if value}


def normalize_task_priority(raw_priority: str | None) -> str:
    """Return a supported task priority, defaulting to medium."""
    priority = (raw_priority or "").strip().lower()
    if priority in TASK_PRIORITY_VALUES:
        return priority
    return DEFAULT_TASK_PRIORITY


def normalize_task_recurrence(raw_recurrence: str | None) -> str | None:
    """Return a supported recurrence value, or None for one-off tasks."""
    recurrence = (raw_recurrence or "").strip().lower()
    if recurrence in TASK_RECURRENCE_VALUES:
        return recurrence
    return None

# --- Updated Theme Constants ---
THEME_OPTIONS = [
    ("light", "Светлый"),   # 1. Default theme identifier
    ("dark", "Темный"),     # 2. Existing dark theme identifier
    ("midnight", "Полуночный"), # 3. Added: Deep blue/Midnight feel
    ("forest", "Лесной"),   # 4. Added: Earthy green/Forest feel
    ("peach", "Персиковый"),  # 5. Added: Warm peach/Soft coral feel
    ("sepia", "Сепия"),      # 6. New theme: Retro, warm brown tones
    ("ocean", "Океан"),     # 7. New theme: Cool blue/Aqua nautical feel
    ("neon", "Неон")         # 8. New theme: Vibrant cyberpunk glow
]
THEME_MAP = {key.lower(): label for key, label in THEME_OPTIONS}
DEFAULT_THEME = "light"

