from datetime import datetime
from app import db


class Notification(db.Model):
    """One in-app notification for one user, created by a real system event."""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(400), nullable=False, default="")
    link = db.Column(db.String(300), nullable=True)       # page that opens when clicked
    category = db.Column(db.String(30), nullable=False, default="general")
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])


class AuditLog(db.Model):
    """Append-only record of who did what. Never edited or deleted from the UI."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    user_name = db.Column(db.String(120), nullable=True)   # snapshot, survives renames
    user_role = db.Column(db.String(20), nullable=True)
    action = db.Column(db.String(40), nullable=False, index=True)   # created / updated / sale / reversed ...
    entity = db.Column(db.String(40), nullable=False, index=True)   # product / sale / user ...
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
