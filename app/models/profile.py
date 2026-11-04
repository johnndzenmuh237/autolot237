from datetime import datetime
from app import db


class UserProfile(db.Model):
    """Extended HR record for a person (manager / seller / worker).

    Kept in its own table so the original users table is untouched.
    Photo and ID scan are stored in the database (not on disk), because the
    hosting disk is wiped on every redeploy but the database is permanent.
    """
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)

    middle_name = db.Column(db.String(80))
    alt_phone = db.Column(db.String(40))
    country = db.Column(db.String(80))
    id_type = db.Column(db.String(40))
    department = db.Column(db.String(80))
    employment_type = db.Column(db.String(40))
    experience = db.Column(db.Text)
    skills = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    access_level = db.Column(db.String(40))

    # seller-only
    sales_target = db.Column(db.Float)
    commission_rate = db.Column(db.Float)
    assigned_products = db.Column(db.Text)        # comma-separated product ids

    photo = db.Column(db.LargeBinary)
    photo_mime = db.Column(db.String(40))
    id_document = db.Column(db.LargeBinary)
    id_doc_mime = db.Column(db.String(60))
    id_doc_name = db.Column(db.String(160))

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship("User", backref=db.backref("profile", uselist=False, cascade="all, delete-orphan"))

    @property
    def has_photo(self):
        return bool(self.photo)

    @property
    def has_id_document(self):
        return bool(self.id_document)

    @property
    def assigned_product_ids(self):
        return [int(x) for x in (self.assigned_products or "").split(",") if x.strip().isdigit()]
