from app.services import inventory_service


def test_create_product(app, db, admin_user):
    product = inventory_service.create_product({
        "name": "USB Key 64GB", "category": "Accessories",
        "stock_quantity": 20, "cost_price": 4000, "min_price": 6000, "max_price": 8000,
    })
    assert product.id is not None
    assert product.stock_quantity == 20
    assert product.inventory_cost_value == 80000


def test_low_stock_detection(app, db, sample_product):
    sample_product.stock_quantity = 2
    sample_product.low_stock_threshold = 3
    db.session.commit()
    assert sample_product.is_low_stock is True


def test_record_stock_purchase_increases_stock_and_logs_expense(app, db, sample_product):
    from app.models.expense import Expense
    before_stock = sample_product.stock_quantity
    before_expense_count = Expense.query.count()

    inventory_service.record_stock_purchase(sample_product, quantity=15, cost_per_item=95000)

    assert sample_product.stock_quantity == before_stock + 15
    assert Expense.query.count() == before_expense_count + 1


def test_inventory_totals(app, db, sample_product):
    totals = inventory_service.get_inventory_totals()
    assert totals["total_items"] >= sample_product.stock_quantity
    assert totals["min_potential_revenue"] >= 0
    assert totals["max_potential_revenue"] >= totals["min_potential_revenue"]


def test_admin_can_add_product_via_route(client, admin_user):
    from tests.test_auth import login
    login(client, "testadmin", "password123")
    response = client.post(
        "/inventory/add",
        data={
            "name": "Wireless Mouse", "category": "Accessories", "stock_quantity": "30",
            "cost_price": "3000", "min_price": "5000", "max_price": "7000",
            "low_stock_threshold": "5",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Wireless Mouse" in response.data
