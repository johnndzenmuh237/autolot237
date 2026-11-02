from app.models.user import User
from app.models.notification import AuditLog


def get_unclaimed_owner():
    """The owner account that exists but has never signed in (or None)."""
    for o in User.query.filter_by(role="owner").all():
        if AuditLog.query.filter_by(user_id=o.id, action="login").count() == 0:
            return o
    return None


def owner_setup_available():
    """The setup page is open only while there is NO owner, or only an owner
    who has never signed in. Once the owner has logged in, nobody else can
    touch the owner account."""
    owners = User.query.filter_by(role="owner").count()
    return owners == 0 or get_unclaimed_owner() is not None
