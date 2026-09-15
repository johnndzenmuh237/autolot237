from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.sale import Sale
from app.utils.helpers import get_period_range

seller_bp = Blueprint("seller", __name__, url_prefix="/seller")


def _summary(seller, start, end):
    sales = seller.sales.filter(
        Sale.created_at >= start, Sale.created_at <= end, Sale.is_returned == False  # noqa: E712
    ).all()
    return {
        "items_sold": sum(s.quantity for s in sales),
        "revenue": sum(s.total_amount for s in sales),
        "profit": sum(s.total_profit for s in sales),
    }


@seller_bp.route("/")
@seller_bp.route("/dashboard")
@login_required
def dashboard():
    t_start, t_end = get_period_range("today")
    w_start, w_end = get_period_range("week")
    m_start, m_end = get_period_range("month")

    recent_sales = current_user.sales.order_by(Sale.created_at.desc()).limit(8).all()

    return render_template(
        "seller/dashboard.html",
        today=_summary(current_user, t_start, t_end),
        week=_summary(current_user, w_start, w_end),
        month=_summary(current_user, m_start, m_end),
        recent_sales=recent_sales,
    )


@seller_bp.route("/my-sales")
@login_required
def my_sales():
    sales = current_user.sales.order_by(Sale.created_at.desc()).all()
    return render_template("seller/my_sales.html", sales=sales)


@seller_bp.route("/my-performance")
@login_required
def my_performance():
    t_start, t_end = get_period_range("today")
    w_start, w_end = get_period_range("week")
    m_start, m_end = get_period_range("month")
    return render_template(
        "seller/my_performance.html",
        today=_summary(current_user, t_start, t_end),
        week=_summary(current_user, w_start, w_end),
        month=_summary(current_user, m_start, m_end),
    )
