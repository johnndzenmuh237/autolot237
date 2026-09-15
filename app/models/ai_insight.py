from datetime import datetime
from app import db


class AIInsight(db.Model):
    __tablename__ = "ai_insights"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False, default="good")  # good, warning, critical
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=True)  # sales, inventory, profit, employee
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AIInsight {self.level} {self.title}>"
