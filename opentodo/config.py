import os
from secrets import token_urlsafe


class Config:
    TEMPLATES_AUTO_RELOAD = os.environ.get("FLASK_TEMPLATES_AUTO_RELOAD", "").lower() in {"1", "true", "yes"}
    DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    SQLALCHEMY_DATABASE_URI = "sqlite:///todo.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or token_urlsafe(32)
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    NOTIFICATIONS_ENABLED = os.environ.get("NOTIFICATIONS_ENABLED", "1").lower() in {"1", "true", "yes"}
    NOTIFICATIONS_POLL_INTERVAL_SECONDS = int(os.environ.get("NOTIFICATIONS_POLL_INTERVAL_SECONDS", "60"))
