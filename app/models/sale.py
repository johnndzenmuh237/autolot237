from datetime import datetime
from app import db


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)
    unit_cost_price = db.Column(db.Float, nullable=False)  # snapshot at time of sale
    selling_price = db.Column(db.Float, nullable=False)  # per unit
    total_amount = db.Column(db.Float, nullable=False)
    total_profit = db.Column(db.Float, nullable=False)

    is_returned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Sale {self.id} product={self.product_id} qty={self.quantity}>"
