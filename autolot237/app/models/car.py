import json
from datetime import datetime
from app import db


class CarListing(db.Model):
    """Vehicle-specific data for a Product that is being sold on the public storefront.

    Kept as a separate table (one-to-one with Product) so the core LedgerIQ
    inventory model never has to know about cars — the dashboard keeps working
    exactly as before, and any Product can optionally have a CarListing attached.
    """
    __tablename__ = "car_listings"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, unique=True)

    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    listing_code = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "LT-014"

    make = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    mileage_km = db.Column(db.Integer, nullable=False, default=0)
    transmission = db.Column(db.String(20), nullable=False, default="automatic")  # automatic/manual
    fuel_type = db.Column(db.String(20), nullable=False, default="petrol")  # petrol/diesel/hybrid/electric
    body_type = db.Column(db.String(30), nullable=False, default="sedan")
    exterior_color = db.Column(db.String(40), nullable=True)
    condition = db.Column(db.String(20), nullable=False, default="used")  # new/used
    vin = db.Column(db.String(40), nullable=True)
    location = db.Column(db.String(120), nullable=True)

    description = db.Column(db.Text, nullable=True)
    features_csv = db.Column(db.Text, nullable=True)  # comma separated feature tags

    main_image = db.Column(db.String(500), nullable=True)
    gallery_json = db.Column(db.Text, nullable=True)  # JSON list of image URLs

    is_featured = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)

    view_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship("Product", backref=db.backref("car_listing", uselist=False))
    order_items = db.relationship("OrderItem", backref="car_listing", lazy="dynamic")

    @property
    def title(self):
        return f"{self.year} {self.make} {self.model}"

    @property
    def price(self):
        return self.product.min_price if self.product else 0

    @property
    def is_available(self):
        return bool(self.product and self.product.is_active and self.product.stock_quantity > 0 and self.is_published)

    @property
    def features(self):
        if not self.features_csv:
            return []
        return [f.strip() for f in self.features_csv.split(",") if f.strip()]

    @property
    def gallery(self):
        if not self.gallery_json:
            return [self.main_image] if self.main_image else []
        try:
            return json.loads(self.gallery_json)
        except (ValueError, TypeError):
            return [self.main_image] if self.main_image else []

    def set_gallery(self, urls):
        self.gallery_json = json.dumps([u for u in urls if u])

    def __repr__(self):
        return f"<CarListing {self.listing_code} {self.title}>"
