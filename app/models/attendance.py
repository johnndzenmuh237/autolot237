from datetime import datetime, date
from app import db


class Attendance(db.Model):
    """One row = one employee marked themselves present on one date.
    There is no 'absent' row by design — if an active employee has no row
    for a given work day, they're absent that day. This keeps the table
    small and means a day with nobody marked never needs a batch job to
    populate 'absent' rows overnight."""
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("user_id", "work_date", name="uq_attendance_user_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("User")

    def __repr__(self):
        return f"<Attendance user={self.user_id} date={self.work_date}>"
