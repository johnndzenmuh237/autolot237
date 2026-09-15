from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.sale import Sale
from app.models.product import Product
from app.models.user import User


def top_products(limit=5, start=None, end=None):
    q = db.session.query(
        Product.id,
        Product.name,
        func.sum(Sale.quantity).label("qty"),
        func.sum(Sale.total_amount).label("revenue"),
        func.sum(Sale.total_profit).label("profit"),
    ).join(Sale, Sale.product_id == Product.id).filter(Sale.is_returned == False)  # noqa: E712

    if start:
        q = q.filter(Sale.created_at >= start)
    if end:
        q = q.filter(Sale.created_at <= end)

    q = q.group_by(Product.id).order_by(func.sum(Sale.total_profit).desc()).limit(limit)
    return q.all()


def slow_moving_products(days=30, max_units_sold=2):
    """Products with high stock but very few sales in the recent window."""
    since = datetime.utcnow() - timedelta(days=days)
    recent_sales = (
        db.session.query(Sale.product_id, func.sum(Sale.quantity).label("qty"))
        .filter(Sale.created_at >= since, Sale.is_returned == False)  # noqa: E712
        .group_by(Sale.product_id)
        .subquery()
    )

    results = (
        db.session.query(Product, func.coalesce(recent_sales.c.qty, 0))
        .outerjoin(recent_sales, Product.id == recent_sales.c.product_id)
        .filter(Product.is_active == True, Product.stock_quantity > 0)  # noqa: E712
        .all()
    )

    slow = [
        (p, qty) for p, qty in results
        if (qty or 0) <= max_units_sold and p.stock_quantity >= p.low_stock_threshold * 2
    ]
    return slow


def seller_performance(start=None, end=None):
    q = db.session.query(
        User.id,
        User.full_name,
        func.coalesce(func.sum(Sale.quantity), 0).label("items_sold"),
        func.coalesce(func.sum(Sale.total_amount), 0).label("revenue"),
        func.coalesce(func.sum(Sale.total_profit), 0).label("profit"),
    ).outerjoin(
        Sale,
        (Sale.seller_id == User.id) & (Sale.is_returned == False)  # noqa: E712
        & ((Sale.created_at >= start) if start else True)
        & ((Sale.created_at <= end) if end else True),
    ).filter(User.role == "seller").group_by(User.id).order_by(func.sum(Sale.total_profit).desc().nullslast())

    return q.all()


def daily_series(days=14):
    """Revenue/profit per day for the last N days, for charting."""
    since = datetime.utcnow() - timedelta(days=days - 1)
    since_date = datetime(since.year, since.month, since.day)

    rows = (
        db.session.query(
            func.date(Sale.created_at).label("day"),
            func.sum(Sale.total_amount).label("revenue"),
            func.sum(Sale.total_profit).label("profit"),
        )
        .filter(Sale.created_at >= since_date, Sale.is_returned == False)  # noqa: E712
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at))
        .all()
    )
    data = {r.day: {"revenue": r.revenue or 0, "profit": r.profit or 0} for r in rows}

    series = []
    for i in range(days):
        d = (since_date + timedelta(days=i)).date()
        key = d.isoformat()
        entry = data.get(key, {"revenue": 0, "profit": 0})
        series.append({"date": key, "revenue": entry["revenue"], "profit": entry["profit"]})
    return series


def category_breakdown(start=None, end=None):
    q = db.session.query(
        Product.category,
        func.sum(Sale.quantity).label("qty"),
        func.sum(Sale.total_amount).label("revenue"),
    ).join(Sale, Sale.product_id == Product.id).filter(Sale.is_returned == False)  # noqa: E712

    if start:
        q = q.filter(Sale.created_at >= start)
    if end:
        q = q.filter(Sale.created_at <= end)

    return q.group_by(Product.category).order_by(func.sum(Sale.total_amount).desc()).all()
