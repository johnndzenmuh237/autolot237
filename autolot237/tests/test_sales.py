import pytest
from app.services.sales_service import record_sale, validate_sale, SaleError, return_sale


def test_record_sale_reduces_stock_and_computes_profit(app, db, sample_product, seller_user):
    before_stock = sample_product.stock_quantity

    sale = record_sale(sample_product, seller_user, quantity=2, selling_price=140000)

    assert sample_product.stock_quantity == before_stock - 2
    assert sale.total_amount == 280000
    assert sale.total_profit == (140000 - sample_product.cost_price) * 2


def test_cannot_oversell_stock(app, db, sample_product, seller_user):
    with pytest.raises(SaleError):
        record_sale(sample_product, seller_user, quantity=sample_product.stock_quantity + 1, selling_price=140000)


def test_cannot_sell_below_minimum_without_override(app, db, sample_product, seller_user):
    with pytest.raises(SaleError):
        validate_sale(sample_product, quantity=1, selling_price=sample_product.min_price - 1000)


def test_admin_override_allows_below_minimum(app, db, sample_product):
    # Should not raise when allow_below_min=True
    validate_sale(sample_product, quantity=1, selling_price=sample_product.min_price - 1000, allow_below_min=True)


def test_return_sale_restocks_product(app, db, sample_product, seller_user):
    stock_before_sale = sample_product.stock_quantity

    sale = record_sale(sample_product, seller_user, quantity=2, selling_price=140000)
    assert sample_product.stock_quantity == stock_before_sale - 2

    return_sale(sale)
    assert sample_product.stock_quantity == stock_before_sale
    assert sale.is_returned is True


def test_seller_can_record_sale_via_route(client, seller_user, sample_product):
    from tests.test_auth import login
    login(client, "testseller", "password123")
    response = client.post(
        "/sales/quick-sale",
        json={"product_id": sample_product.id, "quantity": 1, "selling_price": 145000},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "Sold 1" in data["message"]


def test_quick_sale_rejects_below_minimum_for_seller(client, seller_user, sample_product):
    from tests.test_auth import login
    login(client, "testseller", "password123")
    response = client.post(
        "/sales/quick-sale",
        json={"product_id": sample_product.id, "quantity": 1, "selling_price": 1000},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
