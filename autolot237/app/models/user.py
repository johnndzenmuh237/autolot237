from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="seller")  # 'admin' or 'seller'
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Employee / HR profile fields ---
    phone = db.Column(db.String(40), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    national_id = db.Column(db.String(60), nullable=True)
    position = db.Column(db.String(80), nullable=True)
    salary = db.Column(db.Float, nullable=True, default=0)
    hire_date = db.Column(db.Date, nullable=True)
    emergency_contact_name = db.Column(db.String(120), nullable=True)
    emergency_contact_phone = db.Column(db.String(40), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    sales = db.relationship("Sale", backref="seller", lazy="dynamic")
    payments = db.relationship(
        "SalaryPayment", backref="employee", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active(self):
        return self.is_active_account

    @property
    def tenure_label(self):
        """Human-readable length of employment, e.g. '1 year, 3 months'."""
        if not self.hire_date:
            return "Not set"
        from datetime import date
        today = date.today()
        start = self.hire_date
        if start > today:
            return "Not started yet"

        years = today.year - start.year
        months = today.month - start.month
        days = today.day - start.day
        if days < 0:
            months -= 1
        if months < 0:
            years -= 1
            months += 12

        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months > 0 or not parts:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        return ", ".join(parts)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
