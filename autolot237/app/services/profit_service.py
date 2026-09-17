from app.models.sale import Sale
from app.models.expense import Expense
from app.utils.helpers import get_period_range


def sales_summary(start, end):
    sales = Sale.query.filter(
        Sale.created_at >= start, Sale.created_at <= end, Sale.is_returned == False  # noqa: E712
    ).all()
    items_sold = sum(s.quantity for s in sales)
    revenue = sum(s.total_amount for s in sales)
    profit = sum(s.total_profit for s in sales)
    return {"items_sold": items_sold, "revenue": revenue, "profit": profit, "count": len(sales)}


def expenses_summary(start, end):
    expenses = Expense.query.filter(Expense.created_at >= start, Expense.created_at <= end).all()
    total = sum(e.amount for e in expenses)
    product_purchases = sum(e.amount for e in expenses if e.category == "Product Purchase")
    other = total - product_purchases
    return {"total": total, "product_purchases": product_purchases, "other": other}


def period_report(period):
    start, end = get_period_range(period)
    sales = sales_summary(start, end)
    expenses = expenses_summary(start, end)
    net_profit = sales["revenue"] - expenses["total"] if period == "month" else sales["profit"]
    return {**sales, "expenses": expenses, "net_profit": net_profit, "start": start, "end": end}
