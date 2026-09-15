import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db as _db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.product import Product  # noqa: E402


class TestConfig:
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CURRENCY_SYMBOL = "CFA"
    LOW_STOCK_DEFAULT_THRESHOLD = 5
    WTF_CSRF_ENABLED = False
    TESTING = True


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    ctx = application.app_context()
    ctx.push()
    yield application
    ctx.pop()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app, db):
    existing = User.query.filter_by(username="testadmin").first()
    if existing:
        return existing
    user = User(full_name="Test Admin", username="testadmin", role="admin")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def seller_user(app, db):
    from datetime import date
    user = User(
        full_name="Test Seller", username="testseller", role="seller",
        phone="+237 600 111 222", address="Douala, Bonanjo", position="Shop Attendant",
        salary=85000, hire_date=date(2026, 1, 1),
    )
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def sample_product(app, db):
    product = Product(
        name="Test Laptop", category="Laptops", stock_quantity=10,
        cost_price=100000, min_price=130000, max_price=160000, low_stock_threshold=3,
    )
    db.session.add(product)
    db.session.commit()
    return product
