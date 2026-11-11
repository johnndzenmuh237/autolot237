from flask import Blueprint, jsonify, request, url_for
from flask_login import login_required, current_user
from app import db
from app.models.push import PushSubscription
from app.utils import push as push_utils
from app.utils.notify import notify_user

push_bp = Blueprint("push", __name__, url_prefix="/push")


@push_bp.route("/config")
@login_required
def config():
    if not push_utils.library_available():
        return jsonify({"enabled": False})
    pub, _ = push_utils.get_vapid_keys()
    mine = PushSubscription.query.filter_by(user_id=current_user.id).count()
    return jsonify({"enabled": True, "publicKey": pub, "subscribed_devices": mine})


@push_bp.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    data = request.get_json(silent=True) or {}
    keys = data.get("keys") or {}
    endpoint, p256dh, auth = data.get("endpoint"), keys.get("p256dh"), keys.get("auth")
    if not (endpoint and p256dh and auth) or not str(endpoint).startswith("https://"):
        return jsonify({"ok": False, "error": "Invalid subscription"}), 400
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if sub:                                  # same phone, maybe a different person signed in
        sub.user_id, sub.p256dh, sub.auth = current_user.id, p256dh, auth
    else:
        db.session.add(PushSubscription(user_id=current_user.id, endpoint=endpoint, p256dh=p256dh, auth=auth,
                                        user_agent=(request.headers.get("User-Agent") or "")[:200]))
    db.session.commit()
    return jsonify({"ok": True})


@push_bp.route("/unsubscribe", methods=["POST"])
@login_required
def unsubscribe():
    endpoint = (request.get_json(silent=True) or {}).get("endpoint")
    if endpoint:
        PushSubscription.query.filter_by(endpoint=endpoint, user_id=current_user.id).delete()
        db.session.commit()
    return jsonify({"ok": True})


@push_bp.route("/test", methods=["POST"])
@login_required
def test():
    """Sends the signed-in user a real notification (bell + pop-up + phone)."""
    notify_user(current_user.id, "Test notification", "If you can read this, notifications are working on this device.",
                link=url_for("notifications.history"), category="general")
    return jsonify({"ok": True})
