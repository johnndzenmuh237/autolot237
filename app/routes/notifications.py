from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


def _mine():
    return Notification.query.filter_by(user_id=current_user.id)


@notifications_bp.route("/")
@login_required
def history():
    items = _mine().order_by(Notification.created_at.desc()).limit(200).all()
    return render_template("notifications/history.html", items=items)


@notifications_bp.route("/api/unread")
@login_required
def api_unread():
    """Polled by the bell every ~20s: unread count + the latest few."""
    latest = _mine().order_by(Notification.created_at.desc()).limit(8).all()
    return jsonify({
        "unread": _mine().filter_by(is_read=False).count(),
        "items": [{
            "id": n.id, "title": n.title, "message": n.message, "is_read": n.is_read,
            "category": n.category, "when": n.created_at.strftime("%d %b %H:%M"),
            "open_url": url_for("notifications.open_item", notification_id=n.id),
        } for n in latest],
    })


@notifications_bp.route("/<int:notification_id>/open")
@login_required
def open_item(notification_id):
    """Mark as read, then go to the record the notification is about."""
    n = _mine().filter_by(id=notification_id).first_or_404()
    n.is_read = True
    db.session.commit()
    link = n.link or url_for("notifications.history")
    return redirect(link if link.startswith("/") and not link.startswith("//") else url_for("notifications.history"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def read_all():
    _mine().filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    if request.accept_mimetypes.best == "application/json":
        return jsonify({"ok": True})
    return redirect(request.referrer or url_for("notifications.history"))
