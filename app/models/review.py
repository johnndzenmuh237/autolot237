from datetime import datetime
from app import db


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    reviewer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=True)  # optional, never displayed publicly
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    # pending / approved / rejected
    is_featured = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    moderated_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Review {self.id} {self.reviewer_name} {self.rating}*>"

    @staticmethod
    def average_rating():
        """Real average across approved reviews only. Returns (avg, count);
        avg is None when there are zero approved reviews — callers must
        handle that by showing an honest empty state, never a fabricated
        number."""
        approved = Review.query.filter_by(status="approved").all()
        if not approved:
            return None, 0
        avg = sum(r.rating for r in approved) / len(approved)
        return round(avg, 1), len(approved)
