from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.models.user import User
from app.utils.decorators import admin_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/staff")
def staff_portal():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "seller.dashboard"))
    return render_template("staff_portal.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Admin login only. Sellers use /seller-login."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "seller.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_account:
            if not user.is_admin:
                flash("That account is a seller account — please use the seller login instead.", "error")
                return redirect(url_for("auth.seller_login"))
            login_user(user, remember=True)
            flash(f"Welcome back, {user.full_name}.", "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("admin.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth_bp.route("/seller-login", methods=["GET", "POST"])
def seller_login():
    """Seller login only. Admins use /login."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "seller.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_account:
            if user.is_admin:
                flash("That account is an admin account — please use the admin login instead.", "error")
                return redirect(url_for("auth.login"))
            login_user(user, remember=True)
            flash(f"Welcome back, {user.full_name}.", "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("seller.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("seller_login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    was_admin = current_user.is_admin
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login" if was_admin else "auth.seller_login"))


@auth_bp.route("/employees/register", methods=["GET", "POST"])
@login_required
@admin_required
def register_seller():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        national_id = request.form.get("national_id", "").strip()
        position = request.form.get("position", "").strip()
        emergency_contact_name = request.form.get("emergency_contact_name", "").strip()
        emergency_contact_phone = request.form.get("emergency_contact_phone", "").strip()
        notes = request.form.get("notes", "").strip()

        salary_raw = request.form.get("salary", "0")
        hire_date_raw = request.form.get("hire_date", "")

        errors = []
        if not full_name or not username or not password:
            errors.append("Full name, username, and password are required.")
        if not phone or not address:
            errors.append("Phone number and address are required for the employee record.")
        if not position:
            errors.append("Position is required.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")

        try:
            salary = float(salary_raw or 0)
        except ValueError:
            errors.append("Salary must be a number.")
            salary = 0

        hire_date = None
        if hire_date_raw:
            try:
                hire_date = datetime.strptime(hire_date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Hire date must be a valid date.")
        else:
            errors.append("Hire date is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/add_employee.html", form=request.form)

        seller = User(
            full_name=full_name, username=username, email=email or None, role="seller",
            phone=phone, address=address, national_id=national_id or None,
            position=position, salary=salary, hire_date=hire_date,
            emergency_contact_name=emergency_contact_name or None,
            emergency_contact_phone=emergency_contact_phone or None,
            notes=notes or None,
        )
        seller.set_password(password)
        db.session.add(seller)
        db.session.commit()
        flash(f"Employee record created for {full_name}.", "success")
        return redirect(url_for("admin.employees"))

    return render_template("admin/add_employee.html", form={})


@auth_bp.route("/employees/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_seller(user_id):
    seller = User.query.get_or_404(user_id)
    if seller.role != "seller":
        flash("Only seller accounts can be toggled here.", "error")
        return redirect(url_for("admin.employees"))
    seller.is_active_account = not seller.is_active_account
    db.session.commit()
    status = "activated" if seller.is_active_account else "deactivated"
    flash(f"{seller.full_name} has been {status}.", "success")
    return redirect(url_for("admin.employees"))
