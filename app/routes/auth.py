from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.models.user import User
from app.utils.decorators import admin_required
from app.utils.notify import notify_roles, log_action

auth_bp = Blueprint("auth", __name__)


def _dashboard_for(user):
    if user.role == "owner":
        return "owner.dashboard"
    if user.is_admin:
        return "admin.dashboard"
    if user.role == "seller":
        return "seller.dashboard"
    return "attendance.mark"  # workers land straight on the attendance page


def _login_route_for(role):
    return {"admin": "auth.login", "owner": "auth.login", "seller": "auth.seller_login", "worker": "auth.worker_login"}.get(role, "auth.staff_portal")


@auth_bp.route("/staff")
def staff_portal():
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user)))
    return render_template("staff_portal.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Manager / Business Owner login. Sellers use /seller-login, workers use /worker-login."""
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_account:
            if user.role not in ("admin", "owner"):
                flash(f"That's a {user.role} account — please use the {user.role} login instead.", "error")
                return redirect(url_for(_login_route_for(user.role)))
            login_user(user, remember=True)
            log_action("login", "user", user.id, f"{user.role_label} signed in")
            flash(f"Welcome back, {user.full_name}.", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for(_dashboard_for(user)))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth_bp.route("/seller-login", methods=["GET", "POST"])
def seller_login():
    """Seller login only. Admins use /login, workers use /worker-login."""
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_account:
            if user.role != "seller":
                flash(f"That's an {user.role} account — please use the {user.role} login instead.", "error")
                return redirect(url_for(_login_route_for(user.role)))
            login_user(user, remember=True)
            flash(f"Welcome back, {user.full_name}.", "success")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("seller.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("seller_login.html")


@auth_bp.route("/worker-login", methods=["GET", "POST"])
def worker_login():
    """Worker login only — for staff who just need to mark attendance, no
    sales tools. Admins use /login, sellers use /seller-login."""
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_for(current_user)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active_account:
            if user.role != "worker":
                flash(f"That's an {user.role} account — please use the {user.role} login instead.", "error")
                return redirect(url_for(_login_route_for(user.role)))
            login_user(user, remember=True)
            flash(f"Welcome back, {user.full_name}.", "success")
            return redirect(url_for("attendance.mark"))

        flash("Invalid username or password.", "error")

    return render_template("worker_login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    was_role = current_user.role
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for(_login_route_for(was_role)))


@auth_bp.route("/employees/register", methods=["GET", "POST"])
@login_required
@admin_required
def register_seller():
    from app.models.product import Product
    from app.utils import people
    kind = request.values.get("role", "seller")
    if kind not in ("seller", "worker"):
        kind = "seller"
    ctx = dict(kind=kind, products=Product.query.filter_by(is_active=True).order_by(Product.name).all(),
               departments=people.STAFF_DEPARTMENTS, genders=people.GENDERS, id_types=people.ID_TYPES,
               employment_types=people.EMPLOYMENT_TYPES, access_levels=people.ACCESS_LEVELS)
    if request.method == "POST":
        data, errors, uploads = people.parse_person(request.form, request.files, kind)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/add_employee.html", form=request.form, **ctx)
        user = people.create_person(data, uploads, request.form["password"], kind,
                                    status_active=request.form.get("account_status", "active") == "active")
        log_action("created", "user", user.id, f"New {kind} account: {user.full_name} ({user.username})")
        notify_roles(("owner",), "New employee account", f"{user.full_name} was added as a {kind}.",
                     link=url_for("admin.employee_profile", user_id=user.id), category="employee")
        flash(f"{kind.capitalize()} {user.full_name} was registered successfully.", "success")
        return redirect(url_for("admin.employees"))
    return render_template("admin/add_employee.html", form=request.form if request.args.get("role") else {}, **ctx)


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
    log_action("updated", "user", seller.id, f"{seller.full_name} {status}")
    notify_roles(("owner",), "Account status changed", f"{seller.full_name} was {status}.",
                 link=url_for("admin.employees"), category="employee")
    flash(f"{seller.full_name} has been {status}.", "success")
    return redirect(url_for("admin.employees"))
