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


def notify_roles(roles, title, message="", link=None, category="general", exclude_self=True):
    """Notify every active user whose role is in `roles`."""
    try:
        actor = _actor()
        users = User.query.filter(User.role.in_(list(roles)), User.is_active_account.is_(True)).all()
        for u in users:
            if exclude_self and actor and u.id == actor.id:
                continue
            db.session.add(Notification(
                user_id=u.id, title=title[:150], message=(message or "")[:400],
                link=link, category=category,
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()


def notify_user(user_id, title, message="", link=None, category="general"):
    try:
        db.session.add(Notification(
            user_id=user_id, title=title[:150], message=(message or "")[:400],
            link=link, category=category,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
