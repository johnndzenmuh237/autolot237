from datetime import datetime, date
from app import db
from app.models.salary_payment import SalaryPayment


def current_period():
    """Return the current calendar period as 'YYYY-MM'."""
    return datetime.utcnow().strftime("%Y-%m")


def _month_range_since(start_date, end_period=None):
    """Yield 'YYYY-MM' strings from start_date's month through end_period (inclusive)."""
    if not start_date:
        return []
    end_period = end_period or current_period()
    end_year, end_month = (int(x) for x in end_period.split("-"))

    periods = []
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_year, end_month):
        periods.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return periods


def get_or_create_payment(user, period=None):
    period = period or current_period()
    payment = SalaryPayment.query.filter_by(user_id=user.id, period=period).first()
    if not payment:
        payment = SalaryPayment(
            user_id=user.id, period=period, amount=user.salary or 0, is_paid=False,
        )
        db.session.add(payment)
        db.session.commit()
    return payment


def payment_history(user):
    """Return SalaryPayment rows for every month since hire_date up to the
    current month, creating any missing rows along the way, newest first."""
    if not user.hire_date:
        return []
    periods = _month_range_since(user.hire_date)
    payments = [get_or_create_payment(user, p) for p in periods]
    return list(reversed(payments))


def mark_paid(payment):
    payment.is_paid = True
    payment.paid_at = datetime.utcnow()
    db.session.commit()
    return payment


def mark_unpaid(payment):
    payment.is_paid = False
    payment.paid_at = None
    db.session.commit()
    return payment


def unpaid_months_count(user):
    return len([p for p in payment_history(user) if not p.is_paid])
