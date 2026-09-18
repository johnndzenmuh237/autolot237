from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.product import Product
from app.models.sale import Sale
from app.services.sales_service import record_sale, SaleError, return_sale
from app.utils.decorators import admin_required, staff_required

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/record")
@login_required
@staff_required
def record():
    products = Product.query.filter_by(is_active=True).order_by(Product.category, Product.name).all()
    return render_template(
        "seller/record_sale.html" if not current_user.is_admin else "admin/record_sale.html",
        products=products,
    )


@sales_bp.route("/quick-sale", methods=["POST"])
@login_required
@staff_required
def quick_sale():
    """Tick-to-sell endpoint: one product, one instant sale, JSON in/out.

    Used by the stock checklist so ticking a box records the sale
    immediately without a full page reload or navigation.
    """
    data = request.get_json(silent=True) or request.form
    product = Product.query.get_or_404(data.get("product_id"))

    try:
        quantity = int(data.get("quantity", 1))
        selling_price = float(data.get("selling_price", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Enter a valid quantity and price."}), 400

    allow_below_min = bool(data.get("allow_below_min")) and current_user.is_admin

    try:
        sale = record_sale(product, current_user, quantity, selling_price, allow_below_min=allow_below_min)
    except SaleError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({
        "success": True,
        "message": f"Sold {sale.quantity} x {product.name} for {sale.total_amount:,.0f}.",
        "stock": product.stock_quantity,
        "total_amount": sale.total_amount,
        "profit": sale.total_profit if current_user.is_admin else None,
    })


@sales_bp.route("/product/<int:product_id>")
@login_required
@staff_required
def product_info(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        "stock": product.stock_quantity,
        "min_price": product.min_price,
        "max_price": product.max_price,
        "cost_price": product.cost_price if current_user.is_admin else None,
    })


@sales_bp.route("/history")
@login_required
@admin_required
def history():
    sales = Sale.query.order_by(Sale.created_at.desc()).limit(200).all()
    return render_template("admin/sales.html", sales=sales)


@sales_bp.route("/<int:sale_id>/return", methods=["POST"])
@login_required
@admin_required
def process_return(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return_sale(sale)
    flash(f"Sale #{sale.id} marked as returned and stock restored.", "success")
    return redirect(url_for("sales.history"))
