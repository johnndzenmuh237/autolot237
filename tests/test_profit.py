from datetime import datetime, timedelta
from app.services.sales_service import record_sale, return_sale
from app.services import profit_service


def test_sales_summary_aggregates_correctly(app, db, sample_product, seller_user):
    record_sale(sample_product, seller_user, quantity=2, selling_price=140000)
    record_sale(sample_product, seller_user, quantity=1, selling_price=150000)

    now = datetime.utcnow()
    start = now - timedelta(days=1)
    summary = profit_service.sales_summary(start, now)

    assert summary["items_sold"] == 3
    assert summary["revenue"] == (2 * 140000) + 150000
    expected_profit = (140000 - sample_product.cost_price) * 2 + (150000 - sample_product.cost_price) * 1
    assert summary["profit"] == expected_profit


def test_expenses_summary_splits_purchases_and_other(app, db):
    from app.models.expense import Expense
    db.session.add(Expense(category="Product Purchase", description="stock", amount=50000))
    db.session.add(Expense(category="Rent", description="shop rent", amount=20000))
    db.session.commit()

    now = datetime.utcnow()
    start = now - timedelta(days=1)
    summary = profit_service.expenses_summary(start, now)

    assert summary["total"] == 70000
    assert summary["product_purchases"] == 50000
    assert summary["other"] == 20000


def test_returned_sale_excluded_from_profit(app, db, sample_product, seller_user):
    sale = record_sale(sample_product, seller_user, quantity=2, selling_price=140000)
    return_sale(sale)

    now = datetime.utcnow()
    start = now - timedelta(days=1)
    summary = profit_service.sales_summary(start, now)
    assert summary["items_sold"] == 0
    assert summary["revenue"] == 0
