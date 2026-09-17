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
from datetime import datetime, timedelta
from app import db
from app.models.ai_insight import AIInsight
from app.services import analytics_service, profit_service
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
