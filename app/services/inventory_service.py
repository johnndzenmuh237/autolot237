from app import db
from app.models.product import Product
from app.models.inventory import InventoryPurchase
from app.models.expense import Expense


def create_product(data):
    product = Product(
        name=data["name"],
        category=data["category"],
        sku=data.get("sku") or None,
        stock_quantity=int(data.get("stock_quantity", 0)),
        cost_price=float(data.get("cost_price", 0)),
        min_price=float(data.get("min_price", 0)),
        max_price=float(data.get("max_price", 0)),
        low_stock_threshold=int(data.get("low_stock_threshold", 5)),
    )
    db.session.add(product)
    db.session.commit()
    return product


def update_product(product, data):
    product.name = data.get("name", product.name)
    product.category = data.get("category", product.category)
    product.sku = data.get("sku") or product.sku
    product.cost_price = float(data.get("cost_price", product.cost_price))
    product.min_price = float(data.get("min_price", product.min_price))
    product.max_price = float(data.get("max_price", product.max_price))
    product.low_stock_threshold = int(data.get("low_stock_threshold", product.low_stock_threshold))
    db.session.commit()
    return product


def record_stock_purchase(product, quantity, cost_per_item, note=None, log_expense=True):
    """Admin records a new inventory purchase; increases stock and logs expense."""
    quantity = int(quantity)
    cost_per_item = float(cost_per_item)
    total_cost = quantity * cost_per_item

    purchase = InventoryPurchase(
        product_id=product.id,
        quantity=quantity,
        cost_per_item=cost_per_item,
        total_cost=total_cost,
        note=note,
    )
    db.session.add(purchase)

    product.stock_quantity += quantity
    # Update the product's standard cost price to the latest purchase cost
    product.cost_price = cost_per_item

    if log_expense:
        expense = Expense(
            category="Product Purchase",
            description=f"Purchased {quantity} x {product.name}",
            amount=total_cost,
        )
        db.session.add(expense)

    db.session.commit()
    return purchase


def get_low_stock_products():
    return [p for p in Product.query.filter_by(is_active=True).all() if p.is_low_stock]


def get_inventory_totals():
    products = Product.query.filter_by(is_active=True).all()
    total_items = sum(p.stock_quantity for p in products)
    inventory_cost = sum(p.inventory_cost_value for p in products)
    min_value = sum(p.min_potential_revenue for p in products)
    max_value = sum(p.max_potential_revenue for p in products)
    return {
        "total_items": total_items,
        "total_products": len(products),
        "inventory_cost": inventory_cost,
        "min_potential_revenue": min_value,
        "max_potential_revenue": max_value,
    }
