from datetime import datetime
from app import db


class InventoryPurchase(db.Model):
    __tablename__ = "inventory_purchases"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cost_per_item = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<InventoryPurchase {self.id} product={self.product_id} qty={self.quantity}>"
