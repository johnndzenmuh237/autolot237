from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True, index=True)
    phone = db.Column(db.String(40), nullable=False, index=True)
    whatsapp = db.Column(db.String(40), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(80), nullable=True)

    password_hash = db.Column(db.String(255), nullable=True)  # set only if they opt into an account

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="customer", lazy="dynamic")
    leads = db.relationship("Lead", backref="customer", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def has_account(self):
        return bool(self.password_hash)

    def __repr__(self):
        return f"<Customer {self.full_name}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    # High-level workflow status.
    # ordered   -> placed, nothing paid yet (pay-on-delivery, or pay-now not yet confirmed)
    # partial   -> some money received, balance still owed
    # paid      -> fully paid -> counted as a real Sale on the dashboard
    # fulfilled -> vehicle handed over / delivered
    # cancelled -> cancelled
    status = db.Column(db.String(20), nullable=False, default="ordered")

    payment_method = db.Column(db.String(30), nullable=False, default="pay_on_delivery")
    # pay_now / pay_on_delivery — how they chose to pay at checkout

    fulfillment_type = db.Column(db.String(20), nullable=False, default="pickup")
    # pickup (at the showroom) / delivery

    shipping_address = db.Column(db.String(255), nullable=True)
    shipping_city = db.Column(db.String(80), nullable=True)
    shipping_notes = db.Column(db.Text, nullable=True)

    subtotal = db.Column(db.Float, nullable=False, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    amount_paid = db.Column(db.Float, nullable=False, default=0)

    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    fulfilled_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship("OrderItem", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("PaymentRecord", backref="order", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def balance_due(self):
        return max(self.total_amount - self.amount_paid, 0)

    @property
    def payment_status(self):
        if self.amount_paid <= 0:
            return "unpaid"
        if self.amount_paid < self.total_amount:
            return "partial"
        return "paid"

    @property
    def status_label(self):
        return {
            "ordered": "Ordered — Pay on Delivery" if self.payment_method == "pay_on_delivery" else "Ordered — Awaiting Payment",
            "partial": "Partially Paid",
            "paid": "Paid & Sold",
            "fulfilled": "Fulfilled",
            "cancelled": "Cancelled",
        }.get(self.status, self.status.title())

    def __repr__(self):
        return f"<Order {self.order_number} {self.status}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    car_listing_id = db.Column(db.Integer, db.ForeignKey("car_listings.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=True)  # set once fully paid

    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    line_total = db.Column(db.Float, nullable=False)

    sale = db.relationship("Sale")
    product = db.relationship("Product")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} car={self.car_listing_id}>"


class PaymentRecord(db.Model):
    """One entry per payment made toward an order — supports partial/deposit payments."""
    __tablename__ = "payment_records"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), nullable=False, default="mobile_money")
    reference = db.Column(db.String(120), nullable=True)

    # Who confirmed it: the customer self-reported it (recorded_by is null),
    # or a staff member confirmed/collected it (recorded_by = that user).
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    recorded_by = db.relationship("User")

    def __repr__(self):
        return f"<PaymentRecord order={self.order_id} amount={self.amount}>"
