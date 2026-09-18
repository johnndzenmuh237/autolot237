"""
Rule-based AI Business Analyst.

Generates plain-language insights from the business's aggregated data:
sales trends, best/slow sellers, profit margins, stock levels, and
employee performance. No external API key is required — this runs
entirely on the store's own numbers. If ANTHROPIC_API_KEY is set in
the environment, insights could be rewritten through the Claude API
for richer language; the deterministic version below is the reliable
fallback and default.
"""
from datetime import datetime, timedelta, date
from app import db
from app.models.ai_insight import AIInsight
from app.services import analytics_service, profit_service, payroll_service
from app.services.inventory_service import get_low_stock_products


def _pct_change(current, previous):
    if not previous:
        return None
    return ((current - previous) / previous) * 100


def generate_insights(persist=True):
    insights = []

    this_month = profit_service.period_report("month")

    # --- Month over month comparison ---
    now = datetime.utcnow()
    first_of_this_month = datetime(now.year, now.month, 1)
    last_month_end = first_of_this_month - timedelta(seconds=1)
    last_month_start = datetime(last_month_end.year, last_month_end.month, 1)
    last_month_sales = profit_service.sales_summary(last_month_start, last_month_end)

    revenue_change = _pct_change(this_month["revenue"], last_month_sales["revenue"])
    if revenue_change is not None:
        if revenue_change >= 5:
            insights.append({
                "level": "good",
                "title": "Sales are trending up",
                "message": (
                    f"Revenue this month is up {revenue_change:.0f}% compared to last month "
                    f"({this_month['revenue']:,.0f} vs {last_month_sales['revenue']:,.0f} "
                    f"{'CFA'}). Keep doing what's working."
                ),
                "category": "sales",
            })
        elif revenue_change <= -5:
            insights.append({
                "level": "critical",
                "title": "Sales are slowing down",
                "message": (
                    f"Revenue this month dropped {abs(revenue_change):.0f}% compared to last "
                    f"month. Consider promotions or checking in with your sellers about what "
                    f"changed."
                ),
                "category": "sales",
            })

    # --- Profit vs revenue relationship ---
    if this_month["revenue"] > 0:
        margin = (this_month["profit"] / this_month["revenue"]) * 100
        if margin < 10:
            insights.append({
                "level": "critical",
                "title": "Profit margin is thin",
                "message": (
                    f"Your profit margin this month is only {margin:.0f}%. Products may be "
                    f"selling too close to their minimum price. Review pricing on your top "
                    f"sellers."
                ),
                "category": "profit",
            })
        elif margin >= 25:
            insights.append({
                "level": "good",
                "title": "Healthy profit margin",
                "message": (
                    f"Your profit margin this month is {margin:.0f}%, which is strong. "
                    f"Revenue is converting well into real profit."
                ),
                "category": "profit",
            })

    # --- Top products ---
    tops = analytics_service.top_products(limit=3, start=first_of_this_month, end=now)
    if tops and this_month["profit"] > 0:
        top_profit_sum = sum(t.profit or 0 for t in tops)
        share = (top_profit_sum / this_month["profit"]) * 100 if this_month["profit"] else 0
        names = ", ".join(t.name for t in tops)
        if share >= 50:
            insights.append({
                "level": "warning",
                "title": "Revenue is concentrated in a few products",
                "message": (
                    f"{names} generated {share:.0f}% of this month's profit. That's good for "
                    f"now, but it's a dependency risk if demand shifts. Consider promoting "
                    f"other product lines."
                ),
                "category": "sales",
            })
        else:
            insights.append({
                "level": "good",
                "title": "Best performing products",
                "message": f"{names} are your strongest performers by profit this month.",
                "category": "sales",
            })

    # --- Slow moving stock ---
    slow = analytics_service.slow_moving_products(days=30, max_units_sold=2)
    if slow:
        names = ", ".join(p.name for p, _ in slow[:3])
        insights.append({
            "level": "warning",
            "title": "Slow-moving stock detected",
            "message": (
                f"{names} have high stock but very few sales in the last 30 days. Consider "
                f"reducing the price or running a promotion to move this inventory."
            ),
            "category": "inventory",
        })

    # --- Low stock alerts ---
    low_stock = get_low_stock_products()
    if low_stock:
        names = ", ".join(p.name for p in low_stock[:4])
        insights.append({
            "level": "warning",
            "title": "Low stock alert",
            "message": (
                f"{names} are running low on stock. Restock soon to avoid missed sales."
            ),
            "category": "inventory",
        })

    # --- Seller performance spread ---
    performers = analytics_service.seller_performance(start=first_of_this_month, end=now)
    performers = [p for p in performers if p.items_sold and p.items_sold > 0]
    if len(performers) >= 2:
        best = performers[0]
        worst = performers[-1]
        if best.profit and worst.profit is not None and best.profit > 0:
            gap = _pct_change(best.profit, worst.profit) if worst.profit else None
            insights.append({
                "level": "good",
                "title": "Top seller this month",
                "message": (
                    f"{best.full_name} generated {best.profit:,.0f} CFA in profit this month, "
                    f"the highest among your sellers."
                ),
                "category": "employee",
            })

    # --- Underperforming seller callout (complements the top-seller one above) ---
    if len(performers) >= 3:
        worst = performers[-1]
        if worst.items_sold and worst.items_sold > 0 and best.profit and worst.profit is not None:
            gap = _pct_change(best.profit, worst.profit)
            if gap is not None and gap >= 60:
                insights.append({
                    "level": "warning",
                    "title": "One seller is falling behind",
                    "message": (
                        f"{worst.full_name} generated {worst.profit:,.0f} CFA in profit this month, "
                        f"well below {best.full_name}'s {best.profit:,.0f} CFA. Consider a check-in "
                        f"to see if they need support, training, or different stock to work with."
                    ),
                    "category": "employee",
                })

    # --- Attendance: who's frequently absent ---
    from app.models.attendance import Attendance
    from app.models.user import User

    staff = User.query.filter(User.role.in_(["seller", "worker"]), User.is_active_account.is_(True)).all()
    since_30d = date.today() - timedelta(days=29)
    total_work_days = (date.today() - since_30d).days + 1
    attendance_rows = Attendance.query.filter(Attendance.work_date >= since_30d).all()
    present_by_user = {}
    for a in attendance_rows:
        present_by_user.setdefault(a.user_id, set()).add(a.work_date)

    frequently_absent = []
    for u in staff:
        present_days = len(present_by_user.get(u.id, set()))
        absent_days = total_work_days - present_days
        rate = (present_days / total_work_days * 100) if total_work_days else 100
        if rate < 50:
            frequently_absent.append((u, absent_days, rate))

    if frequently_absent:
        frequently_absent.sort(key=lambda x: x[2])
        names = ", ".join(f"{u.full_name} ({rate:.0f}% present)" for u, _, rate in frequently_absent[:3])
        insights.append({
            "level": "critical",
            "title": "Attendance concerns",
            "message": (
                f"{names} — attendance over the last 30 days is below 50%. Frequent absence "
                f"affects sales coverage and customer response time. Consider a direct "
                f"conversation to understand what's going on."
            ),
            "category": "employee",
        })
    elif staff and attendance_rows:
        insights.append({
            "level": "good",
            "title": "Attendance is healthy",
            "message": "No employee has fallen below 50% attendance in the last 30 days.",
            "category": "employee",
        })

    # --- Unpaid salaries ---
    unpaid = []
    for u in staff:
        payment = payroll_service.get_or_create_payment(u)
        if not payment.is_paid and (u.salary or 0) > 0:
            unpaid.append(u)

    if unpaid:
        names = ", ".join(u.full_name for u in unpaid[:4])
        total_owed = sum(u.salary or 0 for u in unpaid)
        insights.append({
            "level": "warning",
            "title": "Unpaid salaries this month",
            "message": (
                f"{names} — {len(unpaid)} employee{'s' if len(unpaid) != 1 else ''} not yet "
                f"paid for this month, totaling {total_owed:,.0f} CFA. Settling payroll on "
                f"time keeps staff morale and attendance healthy."
            ),
            "category": "payroll",
        })

    if not insights:
        insights.append({
            "level": "good",
            "title": "All quiet",
            "message": "No unusual patterns detected yet. Record more sales to unlock deeper insights.",
            "category": "general",
        })

    if persist:
        for i in insights:
            db.session.add(AIInsight(
                level=i["level"], title=i["title"], message=i["message"], category=i["category"]
            ))
        db.session.commit()

    return insights
