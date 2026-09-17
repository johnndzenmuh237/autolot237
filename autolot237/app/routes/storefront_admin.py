from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.utils.decorators import admin_required, staff_required
from app.models.product import Product
from app.models.car import CarListing
from app.models.order import Order
from app.models.lead import Lead
from app.utils.codes import slugify, unique_slug, next_listing_code
from app.services.storefront_service import confirm_payment, cancel_order, CheckoutError

store_admin_bp = Blueprint("store_admin", __name__, url_prefix="/admin/store")


# --------------------------------------------------------------- orders ----
# Visible to both admins and sellers — website orders (with customer
# location/shipping/contact details) show up on both dashboards.

@store_admin_bp.route("/orders")
@login_required
@staff_required
def orders():
    status = request.args.get("status", "")
    q = Order.query.order_by(Order.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    return render_template("admin/storefront_orders.html", orders=q.limit(200).all(), status=status)


@store_admin_bp.route("/orders/<order_number>")
@login_required
@staff_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("admin/storefront_order_detail.html", order=order)


@store_admin_bp.route("/orders/<order_number>/record-payment", methods=["POST"])
@login_required
@staff_required
def record_payment(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    amount_raw = request.form.get("amount", "").strip()
    method = request.form.get("method", "cash")
    reference = request.form.get("reference", "").strip() or None

    try:
        amount = float(amount_raw)
        confirm_payment(order, amount, method=method, reference=reference, recorded_by=current_user)
        flash(f"Payment of {amount:,.0f} recorded for order {order.order_number}.", "success")
    except (ValueError, CheckoutError) as exc:
        flash(str(exc) if isinstance(exc, CheckoutError) else "Enter a valid amount.", "error")

    return redirect(url_for("store_admin.order_detail", order_number=order_number))


@store_admin_bp.route("/orders/<order_number>/status", methods=["POST"])
@login_required
@staff_required
def update_order_status(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    new_status = request.form.get("status")

    if new_status == "cancelled":
        try:
            cancel_order(order)
            flash(f"Order {order.order_number} cancelled and stock released.", "success")
        except CheckoutError as exc:
            flash(str(exc), "error")
    elif new_status == "fulfilled":
        order.status = "fulfilled"
        order.fulfilled_at = datetime.utcnow()
        db.session.commit()
        flash(f"Order {order.order_number} marked as fulfilled.", "success")

    return redirect(url_for("store_admin.order_detail", order_number=order_number))


# ---------------------------------------------------------------- leads ----
# Admin-only — the sales-team CRM inbox.

@store_admin_bp.route("/leads")
@login_required
@admin_required
def leads():
    status = request.args.get("status", "")
    q = Lead.query.order_by(Lead.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    return render_template("admin/storefront_leads.html", leads=q.limit(300).all(), status=status)


@store_admin_bp.route("/leads/<int:lead_id>/status", methods=["POST"])
@login_required
@admin_required
def update_lead_status(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    new_status = request.form.get("status")
    if new_status in ("new", "contacted", "won", "lost"):
        lead.status = new_status
        db.session.commit()
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "status": lead.status})
    return redirect(url_for("store_admin.leads"))


# ------------------------------------------------------------- listings ----

@store_admin_bp.route("/cars")
@login_required
@admin_required
def cars():
    listings = CarListing.query.order_by(CarListing.created_at.desc()).all()
    return render_template("admin/storefront_cars.html", listings=listings)


@store_admin_bp.route("/cars/seed-demo", methods=["POST"])
@login_required
@admin_required
def seed_demo():
    """Seeds the ~49 demo car listings directly into whichever database this
    running app is actually using — the fix for a live deployment (Render,
    etc.) whose production database is empty even though your local machine
    has data, since local seeding never touches the live site's database."""
    from app.utils.demo_data import seed_demo_cars
    added, skipped = seed_demo_cars()
    if added:
        flash(f"Added {added} demo car(s) to your live inventory.", "success")
    else:
        flash(f"Nothing to add — all {skipped} demo cars are already in your database.", "info")
    return redirect(url_for("store_admin.cars"))


@store_admin_bp.route("/cars/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_car():
    if request.method == "POST":
        form = request.form
        product = Product(
            name=f"{form.get('year')} {form.get('make')} {form.get('model')}",
            category="Cars",
            sku=form.get("vin") or None,
            stock_quantity=int(form.get("stock_quantity", 1)),
            cost_price=float(form.get("cost_price", 0) or 0),
            min_price=float(form.get("price", 0) or 0),
            max_price=float(form.get("price", 0) or 0),
        )
        db.session.add(product)
        db.session.flush()

        title_for_slug = f"{form.get('year')} {form.get('make')} {form.get('model')}"
        gallery = [u.strip() for u in form.get("gallery_urls", "").splitlines() if u.strip()]

        listing = CarListing(
            product_id=product.id,
            slug=unique_slug(title_for_slug, lambda s: CarListing.query.filter_by(slug=s).first() is not None),
            listing_code=next_listing_code(lambda c: CarListing.query.filter_by(listing_code=c).first() is not None),
            make=form.get("make", "").strip(),
            model=form.get("model", "").strip(),
            year=int(form.get("year")),
            mileage_km=int(form.get("mileage_km", 0) or 0),
            transmission=form.get("transmission", "automatic"),
            fuel_type=form.get("fuel_type", "petrol"),
            body_type=form.get("body_type", "sedan"),
            exterior_color=form.get("exterior_color") or None,
            condition=form.get("condition", "used"),
            vin=form.get("vin") or None,
            location=form.get("location") or None,
            description=form.get("description") or None,
            features_csv=form.get("features") or None,
            main_image=gallery[0] if gallery else None,
            is_featured=bool(form.get("is_featured")),
            is_published=True,
        )
        listing.set_gallery(gallery)
        db.session.add(listing)
        db.session.commit()
        flash(f"{listing.title} published to the storefront.", "success")
        return redirect(url_for("store_admin.cars"))

    return render_template("admin/storefront_car_form.html", listing=None)


@store_admin_bp.route("/cars/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_car(listing_id):
    listing = CarListing.query.get_or_404(listing_id)
    product = listing.product

    if request.method == "POST":
        form = request.form
        product.name = f"{form.get('year')} {form.get('make')} {form.get('model')}"
        product.stock_quantity = int(form.get("stock_quantity", product.stock_quantity))
        product.cost_price = float(form.get("cost_price", product.cost_price) or 0)
        product.min_price = float(form.get("price", product.min_price) or 0)
        product.max_price = product.min_price

        listing.make = form.get("make", listing.make).strip()
        listing.model = form.get("model", listing.model).strip()
        listing.year = int(form.get("year", listing.year))
        listing.mileage_km = int(form.get("mileage_km", listing.mileage_km) or 0)
        listing.transmission = form.get("transmission", listing.transmission)
        listing.fuel_type = form.get("fuel_type", listing.fuel_type)
        listing.body_type = form.get("body_type", listing.body_type)
        listing.exterior_color = form.get("exterior_color") or listing.exterior_color
        listing.condition = form.get("condition", listing.condition)
        listing.vin = form.get("vin") or listing.vin
        listing.location = form.get("location") or listing.location
        listing.description = form.get("description") or listing.description
        listing.features_csv = form.get("features") or listing.features_csv
        listing.is_featured = bool(form.get("is_featured"))
        listing.is_published = bool(form.get("is_published"))

        gallery = [u.strip() for u in form.get("gallery_urls", "").splitlines() if u.strip()]
        if gallery:
            listing.set_gallery(gallery)
            listing.main_image = gallery[0]

        db.session.commit()
        flash(f"{listing.title} updated.", "success")
        return redirect(url_for("store_admin.cars"))

    return render_template("admin/storefront_car_form.html", listing=listing)


@store_admin_bp.route("/cars/<int:listing_id>/unpublish", methods=["POST"])
@login_required
@admin_required
def unpublish_car(listing_id):
    listing = CarListing.query.get_or_404(listing_id)
    listing.is_published = not listing.is_published
    db.session.commit()
    return redirect(url_for("store_admin.cars"))


# --------------------------------------------------------------- reviews ---
# Admin-only — customer reviews are never auto-published; every one is
# approved, rejected, edited, deleted, or featured by a human first.

@store_admin_bp.route("/reviews")
@login_required
@admin_required
def reviews():
    from app.models.review import Review
    status = request.args.get("status", "")
    q = Review.query.order_by(Review.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    return render_template("admin/storefront_reviews.html", reviews=q.all(), status=status)


@store_admin_bp.route("/reviews/<int:review_id>/status", methods=["POST"])
@login_required
@admin_required
def review_status(review_id):
    from app.models.review import Review
    from datetime import datetime
    review = Review.query.get_or_404(review_id)
    new_status = request.form.get("status")
    if new_status in ("approved", "rejected", "pending"):
        review.status = new_status
        review.moderated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Review by {review.reviewer_name} marked as {new_status}.", "success")
    return redirect(url_for("store_admin.reviews"))


@store_admin_bp.route("/reviews/<int:review_id>/feature", methods=["POST"])
@login_required
@admin_required
def review_feature(review_id):
    from app.models.review import Review
    review = Review.query.get_or_404(review_id)
    review.is_featured = not review.is_featured
    db.session.commit()
    return redirect(url_for("store_admin.reviews"))


@store_admin_bp.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def review_edit(review_id):
    from app.models.review import Review
    review = Review.query.get_or_404(review_id)
    if request.method == "POST":
        review.reviewer_name = request.form.get("reviewer_name", review.reviewer_name).strip()
        review.comment = request.form.get("comment", review.comment).strip()
        rating = request.form.get("rating", type=int)
        if rating and 1 <= rating <= 5:
            review.rating = rating
        db.session.commit()
        flash("Review updated.", "success")
        return redirect(url_for("store_admin.reviews"))
    return render_template("admin/storefront_review_edit.html", review=review)


@store_admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
@admin_required
def review_delete(review_id):
    from app.models.review import Review
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review deleted.", "success")
    return redirect(url_for("store_admin.reviews"))
