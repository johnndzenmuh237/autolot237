import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


def _database_uri():
    """Reads DATABASE_URL from the environment, falling back to local SQLite
    if it's missing OR blank (some hosts, like Render, keep an env var
    present with an empty value rather than omitting it entirely — a plain
    os.environ.get() default doesn't catch that case, so we check for it
    explicitly here)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{os.path.join(basedir, 'instance', 'business.db')}"
    # Render/Heroku-style Postgres URLs use the "postgres://" scheme, which
    # older SQLAlchemy versions reject — normalize it to "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "CFA")
    LOW_STOCK_DEFAULT_THRESHOLD = int(os.environ.get("LOW_STOCK_DEFAULT_THRESHOLD", 5))
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True
