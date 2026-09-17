from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.expense import Expense
from app.models.inventory import InventoryPurchase
from app.utils.decorators import admin_required

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")

EXPENSE_CATEGORIES = ["Rent", "Utilities", "Transport", "Salaries", "Marketing", "Maintenance", "Other"]


@expenses_bp.route("/")
@login_required
@admin_required
def list_expenses():
    expenses = Expense.query.order_by(Expense.created_at.desc()).limit(100).all()
    total = sum(e.amount for e in expenses)
    return render_template("admin/expenses.html", expenses=expenses, total=total, categories=EXPENSE_CATEGORIES)


@expenses_bp.route("/add", methods=["POST"])
@login_required
@admin_required
def add_expense():
    try:
        category = request.form.get("category", "Other")
        description = request.form.get("description", "")
        amount = float(request.form.get("amount", 0))
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        expense = Expense(category=category, description=description, amount=amount)
        db.session.add(expense)
        db.session.commit()
        flash("Expense recorded.", "success")
    except (ValueError, TypeError) as e:
        flash(f"Could not record expense: {e}", "error")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/purchases")
@login_required
@admin_required
def purchases():
    records = InventoryPurchase.query.order_by(InventoryPurchase.created_at.desc()).limit(100).all()
    total = sum(p.total_cost for p in records)
    return render_template("admin/purchases.html", purchases=records, total=total)
