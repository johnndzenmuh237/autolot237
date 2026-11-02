from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.notification import AuditLog
from app.services import inventory_service, profit_service, analytics_service
from app.utils.decorators import owner_required
from app.utils.notify import log_action, notify_user
from app.utils.owner_setup import get_unclaimed_owner, owner_setup_available

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")


@owner_bp.route("/")
@owner_bp.route("/dashboard")
@login_required
@owner_required
def dashboard():
    month = profit_service.period_report("month")
    today = profit_service.period_report("today")
    week = profit_service.period_report("week")
    totals = inventory_service.get_inventory_totals()
    series = analytics_service.daily_series(days=14)
    activity = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()
    staff = User.query.filter(User.role.in_(["seller", "worker"]), User.is_active_account.is_(True)).count()
    managers = User.query.filter_by(role="admin").order_by(User.created_at.desc()).all()
    return render_template("owner/dashboard.html", month=month, today=today, week=week,
                           inventory_totals=totals, series=series, activity=activity,
                           staff_count=staff, managers=managers)


@owner_bp.route("/activity")
@login_required
@owner_required
def activity():
    q = AuditLog.query
    entity = request.args.get("entity")
    if entity:
        q = q.filter_by(entity=entity)
    logs = q.order_by(AuditLog.created_at.desc()).limit(300).all()
    entities = [e[0] for e in db.session.query(AuditLog.entity).distinct().order_by(AuditLog.entity).all()]
    return render_template("owner/activity.html", logs=logs, entities=entities, selected=entity)


@owner_bp.route("/managers", methods=["GET", "POST"])
@login_required
@owner_required
def managers():
    """The ONLY records the owner can change: manager login + status."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        replace = request.form.get("replace_current") == "on"
        errors = []
        if not full_name or not username:
            errors.append("Full name and username are required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            if replace:  # revoke the old manager(s) immediately; no records are touched
                for old in User.query.filter_by(role="admin", is_active_account=True).all():
                    old.is_active_account = False
                    log_action("deactivated", "user", old.id, f"Manager {old.full_name} replaced")
            m = User(full_name=full_name, username=username, role="admin",
                     position="Manager", phone=request.form.get("phone", "").strip() or None)
            m.set_password(password)
            db.session.add(m)
            db.session.commit()
            log_action("created", "user", m.id, f"New manager account: {full_name} ({username})")
            flash(f"Manager account created for {full_name}." + (" Previous manager access revoked." if replace else ""), "success")
            return redirect(url_for("owner.managers"))
    managers_list = User.query.filter_by(role="admin").order_by(User.is_active_account.desc(), User.created_at.desc()).all()
    return render_template("owner/managers.html", managers=managers_list)


@owner_bp.route("/managers/<int:user_id>/toggle", methods=["POST"])
@login_required
@owner_required
def toggle_manager(user_id):
    m = User.query.filter_by(id=user_id, role="admin").first_or_404()
    m.is_active_account = not m.is_active_account
    db.session.commit()
    state = "reactivated" if m.is_active_account else "deactivated (access revoked)"
    log_action("updated", "user", m.id, f"Manager {m.full_name} {state}")
    flash(f"Manager {m.full_name} {state}.", "success")
    return redirect(url_for("owner.managers"))


@owner_bp.route("/managers/<int:user_id>/reset-password", methods=["POST"])
@login_required
@owner_required
def reset_manager_password(user_id):
    m = User.query.filter_by(id=user_id, role="admin").first_or_404()
    password = request.form.get("password", "")
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
    else:
        m.set_password(password)
        db.session.commit()
        log_action("updated", "user", m.id, f"Password reset for manager {m.full_name}")
        notify_user(m.id, "Your password was reset", "The Business Owner reset your password.", category="security")
        flash(f"Password reset for {m.full_name}.", "success")
    return redirect(url_for("owner.managers"))


@owner_bp.route("/my-password", methods=["POST"])
@login_required
@owner_required
def change_my_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    if not current_user.check_password(current):
        flash("Current password is incorrect.", "error")
    elif len(new) < 8:
        flash("New password must be at least 8 characters.", "error")
    else:
        current_user.set_password(new)
        db.session.commit()
        log_action("updated", "user", current_user.id, "Owner changed own password")
        flash("Your password was changed.", "success")
    return redirect(url_for("owner.managers"))


@owner_bp.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    """First-time Business Owner setup, done by the signed-in Manager.
    Open only while no owner has ever signed in; then it closes for good."""
    if current_user.role != "admin":
        abort(403)
    if not owner_setup_available():
        flash("The Business Owner account is already set up.", "info")
        return redirect(url_for("admin.dashboard"))

    existing = get_unclaimed_owner()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip() or "Business Owner"
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        errors = []
        if not username:
            errors.append("Username is required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("The two passwords do not match.")
        clash = User.query.filter_by(username=username).first()
        if clash and (not existing or clash.id != existing.id):
            errors.append("That username is already taken.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            if existing:
                existing.username, existing.full_name = username, full_name
                owner = existing
            else:
                owner = User(username=username, full_name=full_name, role="owner", position="Business Owner")
                db.session.add(owner)
            owner.set_password(password)
            owner.is_active_account = True
            db.session.commit()
            log_action("created", "user", owner.id, f"Business Owner account set up: {username}")
            flash(f"Business Owner account ready. Sign out, then sign in at /login as '{username}'.", "success")
            return redirect(url_for("admin.dashboard"))
    return render_template("owner/setup.html", existing=existing)
