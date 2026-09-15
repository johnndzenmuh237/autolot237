import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'business.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "CFA")
    LOW_STOCK_DEFAULT_THRESHOLD = int(os.environ.get("LOW_STOCK_DEFAULT_THRESHOLD", 5))
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True
