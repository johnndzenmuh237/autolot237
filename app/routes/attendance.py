from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models.user import User
from app.models.attendance import Attendance
from app.utils.decorators import admin_required, any_staff_required

attendance_bp = Blueprint("attendance", __name__)


def _dashboard_endpoint_for(user):
    if user.is_admin:
        return "admin.dashboard"
    if user.role == "seller":
        return "seller.dashboard"
    return "attendance.mark"


# ------------------------------------------------------- any staff member ---

@attendance_bp.route("/attendance", methods=["GET", "POST"])
@login_required
@any_staff_required
def mark():
    today = date.today()

    if request.method == "POST":
        existing = Attendance.query.filter_by(user_id=current_user.id, work_date=today).first()
        if not existing:
            db.session.add(Attendance(user_id=current_user.id, work_date=today))
            db.session.commit()
            flash(f"Marked present for {today.strftime('%A, %d %B %Y')}.", "success")
        return redirect(url_for("attendance.mark"))

    marked_today = Attendance.query.filter_by(user_id=current_user.id, work_date=today).first() is not None

    since = today - timedelta(days=13)
    recent = (
        Attendance.query
        .filter(Attendance.user_id == current_user.id, Attendance.work_date >= since)
        .order_by(Attendance.work_date.desc())
        .all()
    )
    recent_dates = {a.work_date for a in recent}
    history = []
    d = today
    for _ in range(14):
        history.append({"date": d, "present": d in recent_dates})
        d -= timedelta(days=1)

    return render_template("attendance/mark.html", today=today, marked_today=marked_today, history=history)


# ------------------------------------------------------------------ admin ---

@attendance_bp.route("/admin/attendance")
@login_required
@admin_required
def roster():
    date_str = request.args.get("date", "")
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        selected_date = date.today()

    employees = (
        User.query
        .filter(User.role.in_(["seller", "worker"]), User.is_active_account.is_(True))
        .order_by(User.full_name)
        .all()
    )
    present_ids = {
        a.user_id for a in Attendance.query.filter_by(work_date=selected_date).all()
    }

    roster_rows = [
        {"user": u, "present": u.id in present_ids}
        for u in employees
    ]

    # last-30-days absence count per employee, for a quick "who's frequently
    # absent" view alongside the single-day roster above
    since = date.today() - timedelta(days=29)
    work_days = [since + timedelta(days=i) for i in range((date.today() - since).days + 1)]
    attendance_30d = Attendance.query.filter(Attendance.work_date >= since).all()
    present_by_user = {}
    for a in attendance_30d:
        present_by_user.setdefault(a.user_id, set()).add(a.work_date)

    absence_summary = []
    for u in employees:
        present_days = len(present_by_user.get(u.id, set()))
        absence_summary.append({
            "user": u,
            "present_days": present_days,
            "total_days": len(work_days),
            "absent_days": len(work_days) - present_days,
        })
    absence_summary.sort(key=lambda r: r["absent_days"], reverse=True)

    return render_template(
        "admin/attendance.html", roster_rows=roster_rows, selected_date=selected_date,
        today=date.today(), absence_summary=absence_summary,
    )
