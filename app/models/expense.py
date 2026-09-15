from datetime import datetime
from app import db


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)  # e.g. Rent, Utilities, Transport
    description = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Expense {self.category} {self.amount}>"
