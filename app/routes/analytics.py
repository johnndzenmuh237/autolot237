from flask import Blueprint, render_template
from flask_login import login_required
from app.utils.decorators import admin_required
from app.services import profit_service, analytics_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/daily")
@login_required
@admin_required
def daily():
    report = profit_service.period_report("today")
    tops = analytics_service.top_products(limit=5, start=report["start"], end=report["end"])
    return render_template("admin/analytics.html", report=report, tops=tops, period_label="Today", period="daily")


@analytics_bp.route("/weekly")
@login_required
@admin_required
def weekly():
    report = profit_service.period_report("week")
    tops = analytics_service.top_products(limit=5, start=report["start"], end=report["end"])
    return render_template("admin/analytics.html", report=report, tops=tops, period_label="This Week", period="weekly")


@analytics_bp.route("/monthly")
@login_required
@admin_required
def monthly():
    report = profit_service.period_report("month")
    tops = analytics_service.top_products(limit=5, start=report["start"], end=report["end"])
    categories = analytics_service.category_breakdown(start=report["start"], end=report["end"])
    return render_template(
        "admin/analytics.html", report=report, tops=tops, categories=categories,
        period_label="This Month", period="monthly",
    )


@analytics_bp.route("/profit")
@login_required
@admin_required
def profit_analysis():
    month = profit_service.period_report("month")
    series = analytics_service.daily_series(days=30)
    tops = analytics_service.top_products(limit=10, start=month["start"], end=month["end"])
    slow = analytics_service.slow_moving_products()
    return render_template(
        "admin/analytics.html", report=month, series=series, tops=tops, slow=slow,
        period_label="Profit Analysis", period="profit",
    )
