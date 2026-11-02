from functools import wraps
from flask import abort, request
from flask_login import current_user

_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def _owner_read_only_ok():
    """The Business Owner may VIEW manager pages but never change anything.
    Enforced here on the server, so hiding buttons is not what protects data."""
    return current_user.role == "owner" and request.method in _SAFE_METHODS


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if not (current_user.is_admin or _owner_read_only_ok()):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    """Business Owner only (their own dashboard and manager-account tools)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "owner":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def seller_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if current_user.role != "seller":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def worker_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if current_user.role != "worker":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def staff_required(f):
    """Admin or seller — used for business pages both share, like the
    Website Orders view. Workers (attendance-only staff) are NOT included —
    use any_staff_required for pages every role should reach."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        if current_user.role not in ("admin", "seller") and not _owner_read_only_ok():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def any_staff_required(f):
    """Admin, seller, or worker — for pages every logged-in staff member
    should reach regardless of role, like marking their own attendance."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        return f(*args, **kwargs)
    return decorated
