from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.product import Product
from app.utils.decorators import admin_required
from app.services import inventory_service

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/")
@login_required
@admin_required
def list_products():
    category = request.args.get("category")
    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    products = query.order_by(Product.category, Product.name).all()
    categories = sorted({p.category for p in Product.query.filter_by(is_active=True).all()})
    return render_template("admin/products.html", products=products, categories=categories, selected_category=category)


@inventory_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_product():
    if request.method == "POST":
        try:
            inventory_service.create_product(request.form)
            flash("Product added to inventory.", "success")
            return redirect(url_for("inventory.list_products"))
        except (ValueError, KeyError) as e:
            flash(f"Could not add product: {e}", "error")
    return render_template("admin/add_product.html")


@inventory_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        try:
            inventory_service.update_product(product, request.form)
            flash("Product updated.", "success")
            return redirect(url_for("inventory.list_products"))
        except (ValueError, KeyError) as e:
            flash(f"Could not update product: {e}", "error")
    return render_template("admin/edit_product.html", product=product)


@inventory_bp.route("/<int:product_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    flash(f"{product.name} removed from active inventory.", "info")
    return redirect(url_for("inventory.list_products"))


@inventory_bp.route("/stock-updates", methods=["GET", "POST"])
@login_required
@admin_required
def stock_updates():
    if request.method == "POST":
        product = Product.query.get_or_404(request.form.get("product_id"))
        try:
            quantity = int(request.form.get("quantity", 0))
            cost_per_item = float(request.form.get("cost_per_item", 0))
            note = request.form.get("note")
            inventory_service.record_stock_purchase(product, quantity, cost_per_item, note=note)
            flash(f"Added {quantity} x {product.name} to stock.", "success")
        except (ValueError, TypeError):
            flash("Please enter a valid quantity and cost.", "error")
        return redirect(url_for("inventory.stock_updates"))

    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    from app.models.inventory import InventoryPurchase
    recent_purchases = InventoryPurchase.query.order_by(InventoryPurchase.created_at.desc()).limit(15).all()
    return render_template("admin/stock_updates.html", products=products, recent_purchases=recent_purchases)


@inventory_bp.route("/low-stock")
@login_required
@admin_required
def low_stock_alerts():
    low_stock = inventory_service.get_low_stock_products()
    return render_template("admin/products.html", products=low_stock, categories=[], selected_category=None, low_stock_view=True)
