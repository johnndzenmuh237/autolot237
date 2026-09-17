from datetime import datetime, timedelta


def ensure_default_admin():
    """Create a default admin account on first run if no users exist.

    Safe to call from multiple worker processes at once (e.g. Gunicorn with
    several workers): if another worker already inserted the row first, the
    resulting IntegrityError is swallowed and we roll back cleanly.
    """
    from sqlalchemy.exc import IntegrityError
    from app import db
    from app.models.user import User

    if User.query.count() == 0:
        admin = User(
            full_name="Business Owner",
            username="admin",
            email="admin@example.com",
            role="admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def get_period_range(period):
    """Return (start_datetime, end_datetime) for 'today', 'week', 'month'."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    if period == "today":
        return today_start, now
    if period == "week":
        start = today_start - timedelta(days=today_start.weekday())
        return start, now
    if period == "month":
        start = datetime(now.year, now.month, 1)
        return start, now
    return today_start, now
