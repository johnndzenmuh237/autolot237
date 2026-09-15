from datetime import datetime
from app import db


class SalaryPayment(db.Model):
    """One row per employee per calendar month (e.g. '2026-08')."""
    __tablename__ = "salary_payments"
    __table_args__ = (
        db.UniqueConstraint("user_id", "period", name="uq_salary_payment_user_period"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    period = db.Column(db.String(7), nullable=False, index=True)  # 'YYYY-MM'
    amount = db.Column(db.Float, nullable=False, default=0)
    is_paid = db.Column(db.Boolean, default=False, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SalaryPayment user={self.user_id} period={self.period} paid={self.is_paid}>"
