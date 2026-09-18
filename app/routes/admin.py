from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.utils.decorators import admin_required
from app.models.user import User
from app.services import inventory_service, profit_service, analytics_service, payroll_service
from app.models.ai_insight import AIInsight

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    inventory_totals = inventory_service.get_inventory_totals()
    low_stock = inventory_service.get_low_stock_products()

    today = profit_service.period_report("today")
    week = profit_service.period_report("week")
    month = profit_service.period_report("month")

    series = analytics_service.daily_series(days=14)
    top = analytics_service.top_products(limit=5, start=month["start"], end=month["end"])
    latest_insights = AIInsight.query.order_by(AIInsight.created_at.desc()).limit(4).all()

    sellers = User.query.filter(User.role.in_(["seller", "worker"]), User.is_active_account.is_(True)).all()
    total_employees = len(sellers)
    monthly_payroll = sum(s.salary or 0 for s in sellers)
    unpaid_this_month = sum(
        1 for s in sellers
        if not payroll_service.get_or_create_payment(s).is_paid
    )

    return render_template(
        "admin/dashboard.html",
        inventory_totals=inventory_totals,
        low_stock=low_stock,
        today=today,
        week=week,
        month=month,
        series=series,
        top_products=top,
        latest_insights=latest_insights,
        total_employees=total_employees,
        monthly_payroll=monthly_payroll,
        unpaid_this_month=unpaid_this_month,
    )


@admin_bp.route("/employees")
@login_required
@admin_required
def employees():
    sellers = User.query.filter(User.role.in_(["seller", "worker"])).order_by(User.full_name).all()
    performance = {p.id: p for p in analytics_service.seller_performance()}
    current_period = payroll_service.current_period()
    payment_status = {
        s.id: payroll_service.get_or_create_payment(s, current_period) for s in sellers
    }
    total_payroll = sum(s.salary or 0 for s in sellers if s.is_active_account)
    return render_template(
        "admin/employees.html",
        sellers=sellers,
        performance=performance,
        payment_status=payment_status,
        total_payroll=total_payroll,
    )


@admin_bp.route("/employees/<int:user_id>/profile")
@login_required
@admin_required
def employee_profile(user_id):
    seller = User.query.get_or_404(user_id)
    from app.models.sale import Sale
    from app.utils.helpers import get_period_range as period_range

    def summary(start, end):
        sales = seller.sales.filter(
            Sale.created_at >= start, Sale.created_at <= end, Sale.is_returned == False  # noqa: E712
        ).all()
        return {
            "items_sold": sum(s.quantity for s in sales),
            "revenue": sum(s.total_amount for s in sales),
            "profit": sum(s.total_profit for s in sales),
        }

    t_start, t_end = period_range("today")
    w_start, w_end = period_range("week")
    m_start, m_end = period_range("month")

    recent_sales = seller.sales.order_by(Sale.created_at.desc()).limit(20).all()
    payments = payroll_service.payment_history(seller)

    return render_template(
        "admin/employee_profile.html",
        seller=seller,
        today=summary(t_start, t_end),
        week=summary(w_start, w_end),
        month=summary(m_start, m_end),
        recent_sales=recent_sales,
        payments=payments,
    )


@admin_bp.route("/employees/<int:user_id>/payments/<period>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_payment(user_id, period):
    seller = User.query.get_or_404(user_id)
    payment = payroll_service.get_or_create_payment(seller, period)
    if payment.is_paid:
        payroll_service.mark_unpaid(payment)
        flash(f"Marked {period} as unpaid for {seller.full_name}.", "info")
    else:
        payroll_service.mark_paid(payment)
        flash(f"Marked {period} as paid for {seller.full_name}.", "success")
    return redirect(request.referrer or url_for("admin.employee_profile", user_id=user_id))
