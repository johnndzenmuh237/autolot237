from datetime import datetime
from app import db


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    car_listing_id = db.Column(db.Integer, db.ForeignKey("car_listings.id"), nullable=True)

    source = db.Column(db.String(20), nullable=False, default="contact_form")
    # whatsapp / ai_chat / contact_form / test_drive

    name = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    message = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="new")
    # new / contacted / won / lost

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    car_listing = db.relationship("CarListing")

    def __repr__(self):
        return f"<Lead {self.source} {self.name or self.phone}>"
