"""Web Push: delivers notifications to phones/computers even when the app is closed.

Keys are created automatically the first time they are needed and stored in
the database, so nothing has to be configured by hand (env vars
VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY override them if you ever want that).
Sending is failure-safe and happens in a background thread, so a slow or
dead push service can never slow down or break a sale or a message.
"""
import json
import os
import threading
from flask import current_app
from app import db
from app.models.push import AppSetting, PushSubscription


def library_available():
    try:
        import pywebpush  # noqa: F401
        return True
    except Exception:
        return False


def _get(key):
    row = AppSetting.query.get(key)
    return row.value if row else None


def get_vapid_keys():
    """Return (public_key_b64url, private_pem). Creates and stores them once."""
    env_pub, env_priv = os.environ.get("VAPID_PUBLIC_KEY"), os.environ.get("VAPID_PRIVATE_KEY")
    if env_pub and env_priv:
        return env_pub, env_priv.replace("\\n", "\n")
    pub, priv = _get("vapid_public"), _get("vapid_private")
    if pub and priv:
        return pub, priv
    from py_vapid import Vapid
    from py_vapid.utils import b64urlencode
    from cryptography.hazmat.primitives import serialization as ser
    v = Vapid()
    v.generate_keys()
    priv = v.private_pem().decode()
    pub = b64urlencode(v.public_key.public_bytes(ser.Encoding.X962, ser.PublicFormat.UncompressedPoint))
    try:
        for k, val in (("vapid_public", pub), ("vapid_private", priv)):
            row = AppSetting.query.get(k)
            if row:
                row.value = val
            else:
                db.session.add(AppSetting(key=k, value=val))
        db.session.commit()
    except Exception:
        db.session.rollback()
        # another worker stored keys first: use theirs so everyone matches
        pub, priv = _get("vapid_public") or pub, _get("vapid_private") or priv
    return pub, priv


def _send_all(app, items):
    """items: list of dicts {user_id, title, body, url, tag}"""
    with app.app_context():
        try:
            from pywebpush import webpush, WebPushException
            from py_vapid import Vapid
            _, priv = get_vapid_keys()
            vapid = Vapid.from_pem(priv.encode())
            subject = os.environ.get("VAPID_SUBJECT", "https://autolot237.onrender.com")
            for it in items:
                subs = PushSubscription.query.filter_by(user_id=it["user_id"]).all()
                payload = json.dumps({"title": it["title"], "body": it["body"], "url": it["url"], "tag": it.get("tag", "")})
                for sub in subs:
                    try:
                        webpush(subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                                data=payload, vapid_private_key=vapid, vapid_claims={"sub": subject},
                                ttl=86400, timeout=8)
                    except WebPushException as e:
                        code = getattr(getattr(e, "response", None), "status_code", None)
                        if code in (404, 410):          # phone uninstalled / revoked permission
                            db.session.delete(sub)
                            db.session.commit()
                    except Exception:
                        pass
        except Exception:
            db.session.rollback()


def send_for_notifications(items):
    """Fire-and-forget. Safe to call from any request."""
    if not items or not library_available():
        return
    app = current_app._get_current_object()
    if app.config.get("PUSH_SYNC"):            # used by the automated tests
        _send_all(app, items)
        return
    threading.Thread(target=_send_all, args=(app, items), daemon=True).start()
