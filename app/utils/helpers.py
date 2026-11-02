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
            full_name="Manager",
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


def ensure_owner_account():
    """Rename the old 'Business Owner' manager label, and create the Business
    Owner account when OWNER_PASSWORD is set in the environment (never uses
    a built-in default password)."""
    import os
    from sqlalchemy.exc import IntegrityError
    from app import db
    from app.models.user import User

    try:
        for u in User.query.filter_by(role="admin", full_name="Business Owner").all():
            u.full_name = "Manager"
        db.session.commit()
    except Exception:
        db.session.rollback()

    password = os.environ.get("OWNER_PASSWORD", "").strip()
    if not password or User.query.filter_by(role="owner").count() > 0:
        return
    username = os.environ.get("OWNER_USERNAME", "owner").strip() or "owner"
    if User.query.filter_by(username=username).first():
        return
    owner = User(full_name=os.environ.get("OWNER_NAME", "Business Owner"), username=username,
                 role="owner", position="Business Owner")
    owner.set_password(password)
    db.session.add(owner)
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
