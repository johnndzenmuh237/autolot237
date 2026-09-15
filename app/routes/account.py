from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from app import db
from app.models.order import Customer
from app.utils.customer_auth import current_customer, customer_login_required

account_bp = Blueprint("account", __name__, url_prefix="/account")


@account_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_customer():
        return redirect(url_for("account.dashboard"))

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        customer = Customer.query.filter_by(phone=phone).first()

        if customer and customer.check_password(password):
            session["customer_id"] = customer.id
            flash(f"Welcome back, {customer.full_name.split(' ')[0]}.", "success")
            return redirect(request.args.get("next") or url_for("account.dashboard"))

        flash("That phone number and password don't match an account — or you checked out as a guest. "
              "You can also just track a specific order using its order number below.", "error")

    return render_template("store/account_login.html")


@account_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_customer():
        return redirect(url_for("account.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")

        if not full_name or not phone or not password:
            flash("Name, phone, and password are all required.", "error")
            return render_template("store/account_signup.html")

        existing = Customer.query.filter_by(phone=phone).first()
        if existing and existing.has_account:
            flash("An account already exists for that phone number — try signing in instead.", "error")
            return redirect(url_for("account.login"))

        if existing:
            existing.full_name = full_name
            existing.email = email or existing.email
            existing.set_password(password)
            customer = existing
        else:
            customer = Customer(full_name=full_name, phone=phone, email=email)
            customer.set_password(password)
            db.session.add(customer)

        db.session.commit()
        session["customer_id"] = customer.id
        flash("Account created — your past and future orders will show up here.", "success")
        return redirect(url_for("account.dashboard"))

    return render_template("store/account_signup.html")


@account_bp.route("/logout")
def logout():
    session.pop("customer_id", None)
    flash("You've been signed out.", "info")
    return redirect(url_for("store.home"))


@account_bp.route("/")
@customer_login_required
def dashboard():
    customer = current_customer()
    orders = customer.orders.order_by(db.desc("created_at")).all()
    return render_template("store/account_dashboard.html", customer=customer, orders=orders)


@account_bp.route("/track", methods=["POST"])
def track_order():
    """Lets a guest (no account) look up one order by number + phone, without logging in."""
    from app.models.order import Order
    order_number = request.form.get("order_number", "").strip()
    phone = request.form.get("phone", "").strip()
    order = Order.query.filter_by(order_number=order_number).first()
    if not order or order.customer.phone != phone:
        flash("We couldn't find an order with that number and phone combination.", "error")
        return redirect(url_for("account.login"))
    return redirect(url_for("store.order_confirmation", order_number=order.order_number))
