"""Automatic notifications + audit trail.

Call these from the code that performs a real action (a sale, a product
update...) — never create notifications by hand. Both helpers are
failure-safe: a problem here must never break the business action itself.
"""
from flask_login import current_user
from app import db
from app.models.user import User
from app.models.notification import Notification, AuditLog


def _actor():
    try:
        if current_user and current_user.is_authenticated:
            return current_user
    except Exception:
        pass
    return None


def log_action(action, entity, entity_id=None, details=None):
    try:
        actor = _actor()
        db.session.add(AuditLog(
            user_id=actor.id if actor else None,
            user_name=actor.full_name if actor else "System",
            user_role=actor.role if actor else None,
            action=action, entity=entity, entity_id=entity_id,
            details=(details or "")[:500],
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _create(user_ids, title, message, link, category):
    """Create one notification per user, then push it to their phones."""
    rows = []
    for uid in user_ids:
        n = Notification(user_id=uid, title=title[:150], message=(message or "")[:400], link=link, category=category)
        db.session.add(n)
        rows.append(n)
    db.session.commit()
    try:
        from flask import url_for
        from app.utils.push import send_for_notifications
        send_for_notifications([{
            "user_id": n.user_id, "title": n.title, "body": n.message, "tag": f"n{n.id}",
            "url": url_for("notifications.open_item", notification_id=n.id),
        } for n in rows])
    except Exception:
        pass


def notify_roles(roles, title, message="", link=None, category="general", exclude_self=True):
    """Notify every active user whose role is in `roles`."""
    try:
        actor = _actor()
        users = User.query.filter(User.role.in_(list(roles)), User.is_active_account.is_(True)).all()
        ids = [u.id for u in users if not (exclude_self and actor and u.id == actor.id)]
        if ids:
            _create(ids, title, message, link, category)
    except Exception:
        db.session.rollback()


def notify_users(user_ids, title, message="", link=None, category="general"):
    """Notify an explicit list of people (used by manager messages)."""
    try:
        ids = list(dict.fromkeys(user_ids))
        if ids:
            _create(ids, title, message, link, category)
    except Exception:
        db.session.rollback()


def notify_user(user_id, title, message="", link=None, category="general"):
    try:
        _create([user_id], title, message, link, category)
    except Exception:
        db.session.rollback()
