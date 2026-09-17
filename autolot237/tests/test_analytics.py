from datetime import datetime, timedelta
from app.services.sales_service import record_sale
from app.services import analytics_service


def test_top_products_ranks_by_profit(app, db, sample_product, seller_user):
    from app.models.product import Product

    product_b = Product(
        name="Budget Laptop", category="Laptops", stock_quantity=10,
        cost_price=90000, min_price=100000, max_price=120000, low_stock_threshold=3,
    )
    db.session.add(product_b)
    db.session.commit()

    record_sale(sample_product, seller_user, quantity=2, selling_price=150000)  # higher profit
    record_sale(product_b, seller_user, quantity=1, selling_price=105000)  # lower profit

    now = datetime.utcnow()
    start = now - timedelta(days=1)
    tops = analytics_service.top_products(limit=5, start=start, end=now)

    assert len(tops) == 2
    # highest profit should be first
    assert tops[0].profit >= tops[1].profit


def test_seller_performance_reports_zero_for_no_sales(app, db, seller_user):
    performance = analytics_service.seller_performance()
    seller_row = [p for p in performance if p.id == seller_user.id][0]
    assert seller_row.items_sold == 0
    assert seller_row.revenue == 0


def test_daily_series_has_correct_length(app, db):
    series = analytics_service.daily_series(days=7)
    assert len(series) == 7
    for entry in series:
        assert "date" in entry
        assert "revenue" in entry
        assert "profit" in entry


def test_slow_moving_products_detects_high_stock_low_sales(app, db):
    from app.models.product import Product
    product = Product(
        name="Old Stock Item", category="Accessories", stock_quantity=100,
        cost_price=1000, min_price=1500, max_price=2000, low_stock_threshold=5,
    )
    db.session.add(product)
    db.session.commit()

    slow = analytics_service.slow_moving_products(days=30, max_units_sold=2)
    names = [p.name for p, _ in slow]
    assert "Old Stock Item" in names
