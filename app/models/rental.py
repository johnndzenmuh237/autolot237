"""Car Rental add-on.

These are brand-new tables that sit alongside the existing sales-oriented
CarListing/Product models without altering them in any way — the same
pattern CarListing already uses to attach car-specific data to Product
(one-to-one companion table). Nothing here changes existing behavior:
a CarListing with no RentalInfo row simply isn't offered for rent, and the
existing sales/checkout flow is completely untouched.
"""
from datetime import datetime
from app import db


RENTAL_STATUSES = ("available", "rented", "unavailable", "maintenance")
BOOKING_STATUSES = ("pending", "approved", "rejected", "active", "completed", "cancelled")

# Booking statuses that actually hold the vehicle for their date range and
# therefore block a new overlapping booking.
_BLOCKING_BOOKING_STATUSES = ("pending", "approved", "active")


class RentalInfo(db.Model):
    """One-to-one companion to CarListing — turns a vehicle into a rentable
    vehicle without touching the CarListing/Product tables used by sales."""
    __tablename__ = "rental_info"

    id = db.Column(db.Integer, primary_key=True)
    car_listing_id = db.Column(db.Integer, db.ForeignKey("car_listings.id"), nullable=False, unique=True)

    is_rentable = db.Column(db.Boolean, default=False, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False, default=0)
    weekly_rate = db.Column(db.Float, nullable=True)
    monthly_rate = db.Column(db.Float, nullable=True)
    seats = db.Column(db.Integer, nullable=True)

    # Manual status set by the business owner — independent of bookings, so
    # a car can be pulled out of the rental pool (maintenance, unavailable)
    # even if it has no active bookings.
    rental_status = db.Column(db.String(20), nullable=False, default="available")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    car_listing = db.relationship("CarListing", backref=db.backref("rental_info", uselist=False))

    @property
    def is_bookable(self):
        return bool(self.is_rentable and self.rental_status == "available" and self.car_listing and self.car_listing.is_published)

    def rate_for(self, days):
        """Best-effort estimated total for a stay of `days` nights, preferring
        monthly/weekly rates when they beat the plain daily rate."""
        if days <= 0:
            return 0
        if days >= 28 and self.monthly_rate:
            months = days // 30 or 1
            remainder = days - months * 30
            return months * self.monthly_rate + max(remainder, 0) * self.daily_rate
        if days >= 7 and self.weekly_rate:
            weeks = days // 7
            remainder = days - weeks * 7
            return weeks * self.weekly_rate + remainder * self.daily_rate
        return days * self.daily_rate

    def __repr__(self):
        return f"<RentalInfo car_listing={self.car_listing_id} status={self.rental_status}>"


class RentalBooking(db.Model):
    __tablename__ = "rental_bookings"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False)
    car_listing_id = db.Column(db.Integer, db.ForeignKey("car_listings.id"), nullable=False)

    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(160), nullable=True)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    total_price = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    car_listing = db.relationship("CarListing", backref=db.backref("rental_bookings", lazy="dynamic"))

    @property
    def nights(self):
        return max((self.end_date - self.start_date).days, 1)

    @classmethod
    def overlaps(cls, car_listing_id, start_date, end_date, exclude_id=None):
        """True if an existing pending/approved/active booking for this
        vehicle overlaps the given date range — the check that prevents two
        customers from successfully renting the same vehicle for overlapping
        dates."""
        q = cls.query.filter(
            cls.car_listing_id == car_listing_id,
            cls.status.in_(_BLOCKING_BOOKING_STATUSES),
            cls.start_date <= end_date,
            cls.end_date >= start_date,
        )
        if exclude_id:
            q = q.filter(cls.id != exclude_id)
        return db.session.query(q.exists()).scalar()

    def __repr__(self):
        return f"<RentalBooking {self.reference} car={self.car_listing_id} {self.status}>"


class VehicleMaintenanceLog(db.Model):
    """Lightweight maintenance/cost log per vehicle, kept as its own table so
    the existing Expense ledger schema never has to change. Feeds the
    per-vehicle cost total shown in Car Rentals \u2192 Vehicle Profitability."""
    __tablename__ = "vehicle_maintenance_logs"

    id = db.Column(db.Integer, primary_key=True)
    car_listing_id = db.Column(db.Integer, db.ForeignKey("car_listings.id"), nullable=False)

    maintenance_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    maintenance_type = db.Column(db.String(80), nullable=False)  # e.g. Oil change, Tires, Repair
    description = db.Column(db.String(255), nullable=True)
    vendor = db.Column(db.String(120), nullable=True)
    cost = db.Column(db.Float, nullable=False, default=0)
    mileage_km = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    car_listing = db.relationship("CarListing", backref=db.backref("maintenance_logs", lazy="dynamic"))

    def __repr__(self):
        return f"<VehicleMaintenanceLog car={self.car_listing_id} {self.maintenance_type} {self.cost}>"


def next_booking_reference():
    import random
    from datetime import datetime as _dt

    while True:
        stamp = _dt.utcnow().strftime("%y%m%d")
        suffix = "".join(random.choices("0123456789", k=4))
        candidate = f"RT-{stamp}-{suffix}"
        if not RentalBooking.query.filter_by(reference=candidate).first():
            return candidate
