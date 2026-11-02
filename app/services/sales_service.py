from app import db
from app.models.sale import Sale
from app.utils.notify import notify_roles, notify_user, log_action


class SaleError(Exception):
    """Raised when a sale cannot be completed."""


def validate_sale(product, quantity, selling_price, allow_below_min=False):
    if quantity <= 0:
        raise SaleError("Quantity must be at least 1.")
    if quantity > product.stock_quantity:
        raise SaleError(
            f"Only {product.stock_quantity} item(s) are currently available in stock."
        )
    if selling_price < product.min_price and not allow_below_min:
        raise SaleError(
            f"Selling price is below the minimum allowed price of "
            f"{product.min_price:,.0f}. Admin approval is required to sell below minimum."
        )
    if product.max_price and selling_price > product.max_price * 1.5:
        # sanity check against wildly high mistaken entries
        raise SaleError("Selling price looks unusually high. Please double-check the amount.")


def record_sale(product, seller, quantity, selling_price, allow_below_min=False):
    validate_sale(product, quantity, selling_price, allow_below_min=allow_below_min)

    total_amount = quantity * selling_price
    total_profit = (selling_price - product.cost_price) * quantity

    sale = Sale(
        product_id=product.id,
        seller_id=seller.id,
        quantity=quantity,
        unit_cost_price=product.cost_price,
        selling_price=selling_price,
        total_amount=total_amount,
        total_profit=total_profit,
    )

    product.stock_quantity -= quantity

    db.session.add(sale)
    db.session.commit()

    # Real-event hooks: audit trail + notify Manager and Business Owner
    from flask import url_for
    log_action("sale", "sale", sale.id,
               f"{quantity} x {product.name} at {selling_price:,.0f} (total {total_amount:,.0f})")
    notify_roles(("admin", "owner"), "New sale recorded",
                 f"{seller.full_name} sold {quantity} x {product.name} for {total_amount:,.0f}. "
                 f"Remaining stock: {product.stock_quantity}.",
                 link=url_for("sales.history"), category="sale")
    if product.is_low_stock:
        notify_roles(("admin", "owner"), "Low stock alert",
                     f"{product.name} is down to {product.stock_quantity} in stock.",
                     link=url_for("inventory.low_stock_alerts"), category="inventory")
    return sale


def return_sale(sale):
    """Reverse a sale: restock the product and mark as returned."""
    if sale.is_returned:
        return sale
    product = sale.product
    product.stock_quantity += sale.quantity
    sale.is_returned = True
    db.session.commit()
    from flask import url_for
    log_action("reversed", "sale", sale.id, f"Sale #{sale.id} returned; {sale.quantity} x {product.name} restocked")
    notify_roles(("owner",), "Sale reversed",
                 f"Sale #{sale.id} ({sale.quantity} x {product.name}) was returned and restocked.",
                 link=url_for("sales.history"), category="sale")
    notify_user(sale.seller_id, "Your sale was reversed",
                f"Sale #{sale.id} ({product.name}) was marked as returned.",
                link=url_for("seller.my_sales"), category="sale")
    return sale
