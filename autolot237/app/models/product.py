from datetime import datetime
from app import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, nullable=True)

    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    cost_price = db.Column(db.Float, nullable=False, default=0)
    min_price = db.Column(db.Float, nullable=False, default=0)
    max_price = db.Column(db.Float, nullable=False, default=0)
    low_stock_threshold = db.Column(db.Integer, nullable=False, default=5)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales = db.relationship("Sale", backref="product", lazy="dynamic")
    purchases = db.relationship("InventoryPurchase", backref="product", lazy="dynamic")

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def inventory_cost_value(self):
        return self.stock_quantity * self.cost_price

    @property
    def min_potential_revenue(self):
        return self.stock_quantity * self.min_price

    @property
    def max_potential_revenue(self):
        return self.stock_quantity * self.max_price

    def __repr__(self):
        return f"<Product {self.name}>"
