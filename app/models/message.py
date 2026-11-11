from datetime import datetime
from app import db


class StaffMessage(db.Model):
    """A message written by the manager to one person, a group, or all staff."""
    __tablename__ = "staff_messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    audience = db.Column(db.String(160), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipients = db.relationship("MessageRecipient", backref="message", cascade="all, delete-orphan",
                                 order_by="MessageRecipient.id")


class MessageRecipient(db.Model):
    __tablename__ = "message_recipients"
    __table_args__ = (db.UniqueConstraint("message_id", "user_id", name="uq_message_user"),)
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("staff_messages.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
