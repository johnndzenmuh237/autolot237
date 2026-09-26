from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.utils.decorators import admin_required, staff_required
from app.models.product import Product
from app.models.car import CarListing
from app.models.order import Order
from app.models.lead import Lead
from app.models.rental import RentalInfo, RentalBooking, VehicleMaintenanceLog, RENTAL_STATUSES, BOOKING_STATUSES
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


@store_admin_bp.route("/cars/repair-visibility", methods=["POST"])
@login_required
@admin_required
def repair_visibility():
    """One-click fix for cars that show 'Published' here in the admin panel
    but don't appear on the public storefront. The storefront only shows a
    car when BOTH CarListing.is_published AND the linked Product.is_active
    are true — this repairs any product whose is_active ended up false/NULL
    (which can happen to rows created before a fix, or through any path that
    didn't set it explicitly) without touching anything else about the car."""
    from app.models.product import Product

    product_ids = [
        row[0] for row in
        db.session.query(Product.id)
        .join(CarListing, CarListing.product_id == Product.id)
        .filter(CarListing.is_published.is_(True))
        .filter(db.or_(Product.is_active.is_(False), Product.is_active.is_(None)))
        .all()
    ]

    fixed = 0
    if product_ids:
        fixed = (
            Product.query.filter(Product.id.in_(product_ids))
            .update({Product.is_active: True}, synchronize_session=False)
        )
        db.session.commit()

    if fixed:
        flash(f"Fixed {fixed} car(s) that were published here but hidden from the storefront.", "success")
    else:
        flash("Nothing to fix — every published car is already visible on the storefront.", "info")
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
            is_active=True,
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
        db.session.flush()

        if form.get("is_rentable"):
            rental = RentalInfo(
                car_listing_id=listing.id,
                is_rentable=True,
                daily_rate=float(form.get("daily_rate", 0) or 0),
                weekly_rate=float(form.get("weekly_rate")) if form.get("weekly_rate") else None,
                monthly_rate=float(form.get("monthly_rate")) if form.get("monthly_rate") else None,
                seats=int(form.get("seats")) if form.get("seats") else None,
                rental_status="available",
            )
            db.session.add(rental)

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

        rental = listing.rental_info
        if form.get("is_rentable"):
            if not rental:
                rental = RentalInfo(car_listing_id=listing.id, rental_status="available")
                db.session.add(rental)
            rental.is_rentable = True
            rental.daily_rate = float(form.get("daily_rate", 0) or 0)
            rental.weekly_rate = float(form.get("weekly_rate")) if form.get("weekly_rate") else None
            rental.monthly_rate = float(form.get("monthly_rate")) if form.get("monthly_rate") else None
            rental.seats = int(form.get("seats")) if form.get("seats") else None
        elif rental:
            rental.is_rentable = False

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


# --------------------------------------------------------------- rentals ---
# Car Rentals management — entirely new section, doesn't touch the existing
# vehicle-management (cars) routes above.

@store_admin_bp.route("/rentals")
@login_required
@staff_required
def rentals():
    status_filter = request.args.get("status", "")
    q = RentalBooking.query.order_by(RentalBooking.created_at.desc())
    if status_filter:
        q = q.filter_by(status=status_filter)
    bookings = q.limit(300).all()

    rentable = (
        CarListing.query.join(RentalInfo)
        .filter(RentalInfo.is_rentable.is_(True))
        .order_by(CarListing.created_at.desc()).all()
    )

    revenue = (
        db.session.query(db.func.coalesce(db.func.sum(RentalBooking.total_price), 0))
        .filter(RentalBooking.status.in_(("approved", "active", "completed")))
        .scalar()
    )
    pending_count = RentalBooking.query.filter_by(status="pending").count()
    active_count = RentalBooking.query.filter_by(status="active").count()

    return render_template(
        "admin/storefront_rentals.html",
        bookings=bookings, rentable=rentable, status_filter=status_filter,
        revenue=revenue, pending_count=pending_count, active_count=active_count,
        booking_statuses=BOOKING_STATUSES, rental_statuses=RENTAL_STATUSES,
    )


@store_admin_bp.route("/rentals/<int:listing_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_rentable(listing_id):
    listing = CarListing.query.get_or_404(listing_id)
    rental = listing.rental_info
    if not rental:
        rental = RentalInfo(car_listing_id=listing.id)
        db.session.add(rental)
    rental.is_rentable = not rental.is_rentable
    if rental.is_rentable and not rental.daily_rate:
        rental.daily_rate = float(request.form.get("daily_rate", 0) or 0)
    db.session.commit()
    flash(f"{listing.title} is {'now' if rental.is_rentable else 'no longer'} listed for rent.", "success")
    return redirect(url_for("store_admin.rentals"))


@store_admin_bp.route("/rentals/<int:listing_id>/rates", methods=["POST"])
@login_required
@admin_required
def update_rental_rates(listing_id):
    listing = CarListing.query.get_or_404(listing_id)
    rental = listing.rental_info
    if not rental:
        flash("Enable this vehicle for rent first.", "error")
        return redirect(url_for("store_admin.rentals"))

    rental.daily_rate = float(request.form.get("daily_rate", rental.daily_rate) or 0)
    rental.weekly_rate = float(request.form.get("weekly_rate")) if request.form.get("weekly_rate") else None
    rental.monthly_rate = float(request.form.get("monthly_rate")) if request.form.get("monthly_rate") else None
    rental.seats = int(request.form.get("seats")) if request.form.get("seats") else None
    new_status = request.form.get("rental_status", rental.rental_status)
    if new_status in RENTAL_STATUSES:
        rental.rental_status = new_status
    db.session.commit()
    flash(f"Rental settings updated for {listing.title}.", "success")
    return redirect(url_for("store_admin.rentals"))


@store_admin_bp.route("/rentals/bookings/<int:booking_id>/status", methods=["POST"])
@login_required
@staff_required
def update_booking_status(booking_id):
    booking = RentalBooking.query.get_or_404(booking_id)
    new_status = request.form.get("status", "")
    if new_status not in BOOKING_STATUSES:
        flash("Invalid status.", "error")
        return redirect(url_for("store_admin.rentals"))

    booking.status = new_status
    # Approving/activating a booking marks the vehicle as rented so it's
    # obvious at a glance; completing/cancelling frees it up again — but
    # never overrides a manual "maintenance"/"unavailable" status the owner
    # set on purpose.
    rental = booking.car_listing.rental_info if booking.car_listing else None
    if rental and rental.rental_status not in ("maintenance", "unavailable"):
        if new_status in ("approved", "active"):
            rental.rental_status = "rented"
        elif new_status in ("completed", "cancelled", "rejected"):
            rental.rental_status = "available"

    db.session.commit()
    flash(f"Booking {booking.reference} marked {new_status}.", "success")
    return redirect(url_for("store_admin.rentals"))


@store_admin_bp.route("/rentals/<int:listing_id>/maintenance", methods=["POST"])
@login_required
@staff_required
def add_maintenance_log(listing_id):
    listing = CarListing.query.get_or_404(listing_id)
    from datetime import datetime as _dt

    date_raw = request.form.get("maintenance_date", "").strip()
    try:
        m_date = _dt.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        m_date = _dt.utcnow().date()

    log = VehicleMaintenanceLog(
        car_listing_id=listing.id,
        maintenance_date=m_date,
        maintenance_type=request.form.get("maintenance_type", "").strip() or "Other",
        description=request.form.get("description", "").strip() or None,
        vendor=request.form.get("vendor", "").strip() or None,
        cost=float(request.form.get("cost", 0) or 0),
        mileage_km=int(request.form.get("mileage_km")) if request.form.get("mileage_km") else None,
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Maintenance record added for {listing.title}.", "success")
    return redirect(url_for("store_admin.rentals"))


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
