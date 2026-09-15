import os
from datetime import datetime
from urllib.parse import quote

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session,
    jsonify, send_file, Response, current_app,
)

from app import db
from app.models.product import Product
from app.models.car import CarListing
from app.models.lead import Lead
from app.models.order import Order
from app.services.storefront_service import (
    reserve_order, get_or_create_customer, confirm_payment, CheckoutError,
)
from app.utils.invoice_pdf import generate_invoice_pdf
from app.utils.ai_chat import answer_customer_question
from app.utils.customer_auth import current_customer

store_bp = Blueprint("store", __name__)

WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "").lstrip("+")
BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "AutoLot237")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000")

CART_KEY = "cart_listing_ids"


def _available_query():
    return (
        CarListing.query.join(Product)
        .filter(CarListing.is_published.is_(True), Product.is_active.is_(True), Product.stock_quantity > 0)
    )


def _cart_listings():
    ids = session.get(CART_KEY, [])
    if not ids:
        return []
    listings = CarListing.query.filter(CarListing.id.in_(ids)).all()
    # preserve order & drop any that sold out / were removed since being added
    by_id = {l.id: l for l in listings if l.is_available}
    return [by_id[i] for i in ids if i in by_id]


@store_bp.context_processor
def inject_store_globals():
    return {
        "business_name": BUSINESS_NAME,
        "whatsapp_number": WHATSAPP_NUMBER,
        "cart_count": len(session.get(CART_KEY, [])),
        "site_url": SITE_URL,
        "current_year": datetime.utcnow().year,
        "business_email": os.environ.get("BUSINESS_EMAIL", "sales@autolot237.com"),
        "business_phone": os.environ.get("BUSINESS_PHONE", ""),
        "business_address": os.environ.get("BUSINESS_ADDRESS", "Bonanjo, Douala, Cameroon"),
        "logged_in_customer": current_customer(),
    }


# ---------------------------------------------------------------- pages ----

@store_bp.route("/")
def home():
    featured = _available_query().filter(CarListing.is_featured.is_(True)).order_by(CarListing.created_at.desc()).limit(6).all()
    if len(featured) < 3:
        featured = _available_query().order_by(CarListing.created_at.desc()).limit(6).all()
    latest = _available_query().order_by(CarListing.created_at.desc()).limit(8).all()
    makes = sorted({c.make for c in _available_query().all()})
    return render_template("store/home.html", featured=featured, latest=latest, makes=makes)


@store_bp.route("/about")
def about():
    return render_template("store/about.html")


@store_bp.route("/cars")
def browse():
    q = _available_query()

    search = request.args.get("q", "").strip()
    make = request.args.get("make", "").strip()
    body_type = request.args.get("body_type", "").strip()
    condition = request.args.get("condition", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "newest")

    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(CarListing.make.ilike(like), CarListing.model.ilike(like)))
    if make:
        q = q.filter(CarListing.make == make)
    if body_type:
        q = q.filter(CarListing.body_type == body_type)
    if condition:
        q = q.filter(CarListing.condition == condition)
    if min_price is not None:
        q = q.filter(Product.min_price >= min_price)
    if max_price is not None:
        q = q.filter(Product.min_price <= max_price)

    if sort == "price_asc":
        q = q.order_by(Product.min_price.asc())
    elif sort == "price_desc":
        q = q.order_by(Product.min_price.desc())
    elif sort == "year_desc":
        q = q.order_by(CarListing.year.desc())
    else:
        q = q.order_by(CarListing.created_at.desc())

    page = request.args.get("page", 1, type=int)
    per_page = 12
    total = q.count()
    cars = q.offset((page - 1) * per_page).limit(per_page).all()

    makes = sorted({c.make for c in _available_query().all()})
    body_types = sorted({c.body_type for c in _available_query().all()})

    return render_template(
        "store/cars.html", cars=cars, makes=makes, body_types=body_types,
        total=total, page=page, per_page=per_page,
        filters=dict(q=search, make=make, body_type=body_type, condition=condition,
                     min_price=min_price, max_price=max_price, sort=sort),
    )


@store_bp.route("/cars/<slug>")
def car_detail(slug):
    listing = CarListing.query.filter_by(slug=slug).first_or_404()
    listing.view_count = (listing.view_count or 0) + 1
    db.session.commit()

    related = (
        _available_query()
        .filter(CarListing.id != listing.id, CarListing.make == listing.make)
        .limit(4).all()
    )
    if len(related) < 4:
        more = _available_query().filter(CarListing.id != listing.id).limit(4).all()
        related = (related + more)[:4]

    return render_template("store/car_detail.html", car=listing, related=related)


@store_bp.route("/cars/<slug>/lead", methods=["POST"])
def car_lead(slug):
    listing = CarListing.query.filter_by(slug=slug).first_or_404()
    data = request.get_json(silent=True) or request.form

    lead = Lead(
        source=data.get("source", "contact_form"),
        car_listing_id=listing.id,
        name=data.get("name"),
        phone=data.get("phone"),
        email=data.get("email"),
        message=data.get("message"),
    )
    db.session.add(lead)
    db.session.commit()

    if request.is_json:
        return jsonify({"success": True, "message": "Thanks — our team will reach out shortly."})
    flash("Thanks — our team will reach out shortly.", "success")
    return redirect(url_for("store.car_detail", slug=slug))


# ---------------------------------------------------------------- cart -----

@store_bp.route("/cart/add/<slug>", methods=["POST"])
def cart_add(slug):
    listing = CarListing.query.filter_by(slug=slug).first_or_404()
    ids = session.get(CART_KEY, [])
    if listing.id not in ids:
        ids.append(listing.id)
    session[CART_KEY] = ids
    if request.is_json:
        return jsonify({"success": True, "cart_count": len(ids)})
    flash(f"{listing.title} added to your cart.", "success")
    return redirect(request.referrer or url_for("store.car_detail", slug=slug))


@store_bp.route("/cart/remove/<int:listing_id>", methods=["POST"])
def cart_remove(listing_id):
    ids = session.get(CART_KEY, [])
    ids = [i for i in ids if i != listing_id]
    session[CART_KEY] = ids
    if request.is_json:
        return jsonify({"success": True, "cart_count": len(ids)})
    return redirect(url_for("store.cart_view"))


@store_bp.route("/cart")
def cart_view():
    cars = _cart_listings()
    total = sum(c.price for c in cars)
    return render_template("store/cart.html", cars=cars, total=total)


# ------------------------------------------------------------- checkout ----

@store_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    cars = _cart_listings()
    if not cars:
        flash("Your cart is empty — add a car first.", "info")
        return redirect(url_for("store.browse"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip() or None
        payment_method = request.form.get("payment_method", "pay_on_delivery")  # pay_now / pay_on_delivery
        fulfillment_type = request.form.get("fulfillment_type", "pickup")  # pickup / delivery
        shipping_address = request.form.get("shipping_address", "").strip() or None
        shipping_city = request.form.get("shipping_city", "").strip() or None
        shipping_notes = request.form.get("shipping_notes", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        account_password = request.form.get("account_password", "").strip() or None

        if not full_name or not phone:
            flash("Please provide your name and phone number.", "error")
            return render_template("store/checkout.html", cars=cars, total=sum(c.price for c in cars))
        if fulfillment_type == "delivery" and not shipping_address:
            flash("Please provide a delivery address, or choose showroom pickup.", "error")
            return render_template("store/checkout.html", cars=cars, total=sum(c.price for c in cars))

        customer = get_or_create_customer(
            full_name, phone, email=email, whatsapp=phone, city=shipping_city,
            address=shipping_address, password=account_password,
        )
        try:
            order = reserve_order(
                customer, cars, payment_method=payment_method, fulfillment_type=fulfillment_type,
                shipping_address=shipping_address, shipping_city=shipping_city,
                shipping_notes=shipping_notes, notes=notes,
            )
        except CheckoutError as exc:
            flash(str(exc), "error")
            return render_template("store/checkout.html", cars=_cart_listings(), total=sum(c.price for c in _cart_listings()))

        session[CART_KEY] = []
        session["customer_id"] = customer.id  # so they can immediately view /account without re-logging in

        if payment_method == "pay_now":
            return redirect(url_for("store.order_pay", order_number=order.order_number))
        return redirect(url_for("store.order_confirmation", order_number=order.order_number))

    return render_template("store/checkout.html", cars=cars, total=sum(c.price for c in cars))


@store_bp.route("/order/<order_number>/pay", methods=["GET"])
def order_pay(order_number):
    """The generated payment invoice — shows the amount due and two ways to
    settle it: pay the full amount now, pay a partial deposit, or (if they
    change their mind) fall back to paying on delivery."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("store/order_pay.html", order=order)


@store_bp.route("/order/<order_number>/confirm-payment", methods=["POST"])
def order_confirm_payment(order_number):
    """Customer self-reports that they've sent payment (Mobile Money / bank
    transfer / card). Since there's no live payment gateway wired in, this is
    a self-declared confirmation — staff can see and reconcile every payment
    on the Website Orders page, and can adjust it there if needed."""
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    amount_raw = request.form.get("amount", "").strip()
    method = request.form.get("method", "mobile_money")

    try:
        amount = float(amount_raw)
        confirm_payment(order, amount, method=method, recorded_by=None)
    except (ValueError, CheckoutError) as exc:
        flash(str(exc) if isinstance(exc, CheckoutError) else "Enter a valid amount.", "error")
        return redirect(url_for("store.order_pay", order_number=order_number))

    return redirect(url_for("store.order_confirmation", order_number=order_number))


@store_bp.route("/order/<order_number>")
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("store/order_confirmation.html", order=order)


@store_bp.route("/invoice/<order_number>.pdf")
def invoice_pdf(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    buf = generate_invoice_pdf(order)
    return send_file(
        buf, mimetype="application/pdf", as_attachment=False,
        download_name=f"invoice-{order.order_number}.pdf",
    )


# --------------------------------------------------------------- AI chat ---

@store_bp.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    reply, escalate = answer_customer_question(message, session_history=history)

    if escalate or "chat_lead_logged" not in session:
        pass  # explicit human handoff is logged client-side via /cars/<slug>/lead or the WhatsApp button

    return jsonify({"reply": reply})


@store_bp.route("/api/chat/handoff", methods=["POST"])
def api_chat_handoff():
    """Called when the visitor asks to talk to a human from the AI widget — logs a lead."""
    data = request.get_json(silent=True) or {}
    lead = Lead(
        source="ai_chat",
        name=data.get("name"),
        phone=data.get("phone"),
        message=data.get("transcript"),
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify({"success": True})


# ------------------------------------------------------------- WhatsApp ----

@store_bp.route("/api/whatsapp-lead", methods=["POST"])
def whatsapp_lead():
    data = request.get_json(silent=True) or {}
    car_slug = data.get("car_slug")
    listing = CarListing.query.filter_by(slug=car_slug).first() if car_slug else None

    lead = Lead(
        source="whatsapp",
        car_listing_id=listing.id if listing else None,
        name=data.get("name"),
        phone=data.get("phone"),
        message=data.get("message"),
    )
    db.session.add(lead)
    db.session.commit()

    if listing:
        text = f"Hi {BUSINESS_NAME}, I'm interested in the {listing.title} ({listing.listing_code})."
    else:
        text = f"Hi {BUSINESS_NAME}, I have a question about a car."

    wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(text)}" if WHATSAPP_NUMBER else None
    return jsonify({"success": True, "whatsapp_url": wa_url})


# Meta / Twilio WhatsApp Business API webhook — wire up once you have real
# credentials. See README_STOREFRONT.md for the exact env vars needed.
@store_bp.route("/webhooks/whatsapp", methods=["GET", "POST"])
def whatsapp_webhook():
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    if request.method == "GET":
        if request.args.get("hub.verify_token") == verify_token and verify_token:
            return request.args.get("hub.challenge", "")
        return "Verification failed", 403

    payload = request.get_json(silent=True) or {}
    # NOTE: parsing here follows the Meta Cloud API message shape. Adjust to
    # match Twilio's payload if that's the provider you connect instead.
    try:
        entry = payload.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]["value"]
        message = change.get("messages", [{}])[0]
        contact = change.get("contacts", [{}])[0]
        lead = Lead(
            source="whatsapp",
            name=contact.get("profile", {}).get("name"),
            phone=message.get("from"),
            message=message.get("text", {}).get("body"),
        )
        db.session.add(lead)
        db.session.commit()
    except (IndexError, KeyError, AttributeError):
        pass

    return jsonify({"status": "received"})


# ------------------------------------------------------------------ SEO ----

@store_bp.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": url_for("store.home", _external=True), "priority": "1.0"},
        {"loc": url_for("store.browse", _external=True), "priority": "0.9"},
    ]
    for car in CarListing.query.filter_by(is_published=True).all():
        pages.append({
            "loc": url_for("store.car_detail", slug=car.slug, _external=True),
            "priority": "0.8",
            "lastmod": (car.updated_at or car.created_at).strftime("%Y-%m-%d"),
        })

    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append("<url>")
        xml.append(f"<loc>{p['loc']}</loc>")
        if p.get("lastmod"):
            xml.append(f"<lastmod>{p['lastmod']}</lastmod>")
        xml.append(f"<priority>{p['priority']}</priority>")
        xml.append("</url>")
    xml.append("</urlset>")
    return Response("".join(xml), mimetype="application/xml")


@store_bp.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /checkout",
        "Disallow: /cart",
        "Disallow: /admin",
        f"Sitemap: {url_for('store.sitemap', _external=True)}",
    ]
    return Response("\n".join(lines), mimetype="text/plain")
