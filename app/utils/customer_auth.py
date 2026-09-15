from functools import wraps
from flask import session, redirect, url_for, request


def current_customer():
    from app.models.order import Customer
    customer_id = session.get("customer_id")
    if not customer_id:
        return None
    return Customer.query.get(customer_id)


def customer_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("customer_id"):
            return redirect(url_for("account.login", next=request.path))
        return f(*args, **kwargs)
    return decorated
