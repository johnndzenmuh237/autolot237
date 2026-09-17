from datetime import datetime

from app import db
from app.models.user import User
from app.models.sale import Sale
from app.models.order import Customer, Order, OrderItem, PaymentRecord
from app.utils.codes import new_order_number


class CheckoutError(Exception):
    pass


def get_or_create_online_seller():
    """Sales made through the public website (once fully paid) are recorded
    under a single system 'seller' account so they show up on the admin
    dashboard exactly like a manually recorded sale — same Sale model, same
    reports, same AI insights."""
    user = User.query.filter_by(username="online-store").first()
    if user:
        return user
    user = User(
        full_name="Online Store",
        username="online-store",
        role="seller",
        is_active_account=True,
    )
    user.set_password(new_order_number())  # random, unguessable; nobody logs in with this account
    db.session.add(user)
    db.session.commit()
    return user


def get_or_create_customer(full_name, phone, email=None, whatsapp=None, address=None, city=None, password=None):
    customer = None
    if email:
        customer = Customer.query.filter_by(email=email).first()
    if not customer and phone:
        customer = Customer.query.filter_by(phone=phone).first()

    if customer:
        customer.full_name = full_name or customer.full_name
        customer.whatsapp = whatsapp or customer.whatsapp
        customer.address = address or customer.address
        customer.city = city or customer.city
        if password and not customer.has_account:
            customer.set_password(password)
        db.session.commit()
        return customer

    customer = Customer(full_name=full_name, phone=phone, email=email, whatsapp=whatsapp, address=address, city=city)
    if password:
        customer.set_password(password)
    db.session.add(customer)
    db.session.commit()
    return customer


def reserve_order(customer, car_listings, payment_method="pay_on_delivery",
                   fulfillment_type="pickup", shipping_address=None, shipping_city=None,
                   shipping_notes=None, notes=None):
    """Places an order and reserves the vehicle(s) (decrements stock) — but does
    NOT record a Sale yet. A Sale is only created once the order is fully paid
    (see confirm_payment below), so the dashboard's revenue figures only ever
    reflect money that has actually been received."""
    if not car_listings:
        raise CheckoutError("Your cart is empty.")

    order = Order(
        order_number=new_order_number(),
        customer=customer,
        payment_method=payment_method,
        fulfillment_type=fulfillment_type,
        shipping_address=shipping_address,
        shipping_city=shipping_city,
        shipping_notes=shipping_notes,
        status="ordered",
        notes=notes,
    )
    db.session.add(order)
    db.session.flush()

    subtotal = 0.0
    for listing in car_listings:
        product = listing.product
        if product.stock_quantity < 1:
            raise CheckoutError(f"{listing.title} was just sold and is no longer available.")

        product.stock_quantity -= 1  # reserve it — no other buyer can also order this car

        item = OrderItem(
            order=order,
            car_listing_id=listing.id,
            product_id=product.id,
            quantity=1,
            unit_price=product.min_price,
            line_total=product.min_price,
        )
        db.session.add(item)
        subtotal += product.min_price

    order.subtotal = subtotal
    order.total_amount = subtotal
    db.session.commit()

    from app.utils.whatsapp_notify import notify_new_order
    notify_new_order(order)  # no-op if WhatsApp API isn't configured; never raises

    return order


def confirm_payment(order, amount, method="mobile_money", reference=None, recorded_by=None):
    """Registers money received toward an order (full or partial).

    - Always logs a PaymentRecord (so partial payments show a running history).
    - Updates Order.amount_paid.
    - Once amount_paid reaches the total, the order becomes 'paid' and a real
      Sale row is created for each item — attributing the seller as whoever
      confirmed it (a staff member) or the system 'Online Store' account if
      the customer self-confirmed a Pay Now payment.
    """
    amount = round(float(amount), 2)
    if amount <= 0:
        raise CheckoutError("Enter a payment amount greater than zero.")
    if amount > order.balance_due + 0.01:
        raise CheckoutError(f"That's more than the remaining balance of {order.balance_due:,.0f}.")

    payment = PaymentRecord(
        order=order, amount=amount, method=method, reference=reference,
        recorded_by=recorded_by,
    )
    db.session.add(payment)

    order.amount_paid = round(order.amount_paid + amount, 2)

    if order.amount_paid >= order.total_amount - 0.01:
        order.status = "paid"
        seller = recorded_by if (recorded_by and recorded_by.role in ("admin", "seller")) else get_or_create_online_seller()
        for item in order.items:
            if item.sale_id:
                continue
            product = item.product
            sale = Sale(
                product_id=product.id,
                seller_id=seller.id,
                quantity=item.quantity,
                unit_cost_price=product.cost_price,
                selling_price=item.unit_price,
                total_amount=item.line_total,
                total_profit=(item.unit_price - product.cost_price) * item.quantity,
            )
            db.session.add(sale)
            db.session.flush()
            item.sale_id = sale.id
    else:
        order.status = "partial"

    db.session.commit()

    from app.utils.whatsapp_notify import notify_payment_received
    notify_payment_received(order, amount, method)  # no-op if not configured; never raises

    return order, payment


def cancel_order(order):
    """Cancels an order and releases any reserved stock (only if nothing has
    been sold yet, i.e. no Sale rows exist)."""
    if order.status in ("paid", "fulfilled"):
        raise CheckoutError("This order is already paid/fulfilled and can't be cancelled from here.")
    for item in order.items:
        item.product.stock_quantity += item.quantity
    order.status = "cancelled"
    db.session.commit()
    return order
