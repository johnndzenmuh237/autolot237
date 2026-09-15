"""Seed the database with demo products, sellers, and sales for testing.

Usage:
    python scripts/seed_data.py
"""
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.sale import Sale  # noqa: E402

PRODUCTS = [
    ("Dell Latitude 5400", "Laptops", 20, 180000, 220000, 260000),
    ("HP EliteBook", "Laptops", 15, 200000, 240000, 280000),
    ("Toshiba Satellite", "Laptops", 10, 150000, 190000, 220000),
    ("Lenovo ThinkPad", "Laptops", 12, 210000, 250000, 290000),
    ("Acer Aspire", "Laptops", 8, 140000, 175000, 210000),
    ("Wireless Mouse", "Accessories", 30, 3000, 5000, 7000),
    ("USB Key 64GB", "Accessories", 50, 4000, 6000, 8000),
    ("External Hard Drive 1TB", "Accessories", 18, 25000, 32000, 40000),
    ("SSD 512GB", "Accessories", 22, 30000, 38000, 45000),
    ("Mechanical Keyboard", "Accessories", 14, 15000, 20000, 26000),
    ("Laptop Charger", "Accessories", 25, 8000, 12000, 16000),
    ("Wireless Headphones", "Accessories", 16, 12000, 18000, 24000),
]

SELLERS = [
    ("John Doe", "john", "+237 677 123 456", "Douala, Akwa", "Shop Attendant", 85000, 210),
    ("Marie Fotso", "marie", "+237 699 234 567", "Douala, Bonapriso", "Senior Sales Associate", 110000, 380),
    ("Paul Nkeng", "paul", "+237 655 345 678", "Douala, Bonamoussadi", "Shop Attendant", 85000, 45),
]


def main():
    app = create_app()
    with app.app_context():
        if Product.query.count() > 1:
            print("Products already exist. Skipping product seed.")
        else:
            for name, category, stock, cost, min_p, max_p in PRODUCTS:
                db.session.add(Product(
                    name=name, category=category, stock_quantity=stock,
                    cost_price=cost, min_price=min_p, max_price=max_p, low_stock_threshold=5,
                ))
            db.session.commit()
            print(f"Seeded {len(PRODUCTS)} products.")

        sellers = []
        for full_name, username, phone, address, position, salary, tenure_days in SELLERS:
            existing = User.query.filter_by(username=username).first()
            if existing:
                sellers.append(existing)
                continue
            seller = User(
                full_name=full_name, username=username, role="seller",
                phone=phone, address=address, position=position, salary=salary,
                hire_date=(datetime.utcnow() - timedelta(days=tenure_days)).date(),
                emergency_contact_name="Not on file",
                emergency_contact_phone=None,
            )
            seller.set_password("seller123")
            db.session.add(seller)
            sellers.append(seller)
        db.session.commit()
        print(f"Ensured {len(sellers)} employee accounts exist (password: seller123).")

        products = Product.query.all()
        if Sale.query.count() == 0:
            for _ in range(120):
                product = random.choice(products)
                seller = random.choice(sellers)
                qty = random.randint(1, 3)
                if product.stock_quantity < qty:
                    continue
                price = random.uniform(product.min_price, product.max_price)
                days_ago = random.randint(0, 45)
                sale = Sale(
                    product_id=product.id,
                    seller_id=seller.id,
                    quantity=qty,
                    unit_cost_price=product.cost_price,
                    selling_price=price,
                    total_amount=price * qty,
                    total_profit=(price - product.cost_price) * qty,
                    created_at=datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
                )
                product.stock_quantity -= qty
                db.session.add(sale)
            db.session.commit()
            print("Seeded demo sales history.")
        else:
            print("Sales already exist. Skipping sales seed.")

        print("\nDone. Login as admin/admin123 or john/seller123, marie/seller123, paul/seller123.")

        # Seed a bit of realistic payroll history so the Employees page isn't empty
        from app.services import payroll_service
        for seller in sellers:
            history = payroll_service.payment_history(seller)
            for payment in history[1:]:  # leave the current month unpaid to demo the "tick to pay" flow
                if not payment.is_paid:
                    payroll_service.mark_paid(payment)
        print("Seeded payroll history (most past months marked paid, current month left unpaid).")


if __name__ == "__main__":
    main()
