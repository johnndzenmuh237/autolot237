"""Outbound WhatsApp notifications — pushes a message to the business's own
WhatsApp number whenever something happens that staff should see immediately
(a new order, a payment coming in), even if nobody's logged into the
dashboard at that moment.

This is different from the customer-facing "Chat on WhatsApp" button
(app/routes/storefront.py, WHATSAPP_NUMBER) which just opens wa.me for a
visitor to message you. This module actively SENDS a message on your
behalf, which requires the WhatsApp Business Cloud API — a wa.me link can't
do that.

Needs three environment variables to actually send anything:
  WHATSAPP_ACCESS_TOKEN     - from your Meta app (System User token, ideally
                               a permanent one, not the 24h test token)
  WHATSAPP_PHONE_NUMBER_ID  - the sending number's ID, from Meta's dashboard
  WHATSAPP_NUMBER           - the number that RECEIVES the alerts (your own
                               business WhatsApp — same variable already
                               used for the click-to-chat button)

If any of these are missing, every function here is a silent no-op — it
logs a debug line and returns False, and never raises, so a missing/expired
WhatsApp token can never break checkout or payment confirmation for a
customer.
"""
import os
import logging

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"


def _config():
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    to_number = os.environ.get("WHATSAPP_NUMBER", "").strip()
    if not (token and phone_number_id and to_number):
        return None
    return token, phone_number_id, to_number


def send_whatsapp_alert(message):
    """Sends a plain-text WhatsApp message to the business's own number.
    Returns True if the API accepted it, False otherwise (including when
    not configured) — never raises."""
    config = _config()
    if not config:
        logger.debug("WhatsApp alert skipped — WHATSAPP_ACCESS_TOKEN / "
                      "WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_NUMBER not fully set.")
        return False

    token, phone_number_id, to_number = config
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"

    try:
        import httpx
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message},
            },
            timeout=8.0,
        )
        if response.status_code >= 400:
            logger.warning("WhatsApp alert failed (%s): %s", response.status_code, response.text[:300])
            return False
        return True
    except Exception as exc:  # network error, timeout, bad token, etc.
        logger.warning("WhatsApp alert failed to send: %s", exc)
        return False


def notify_new_order(order):
    currency = os.environ.get("CURRENCY_SYMBOL", "CFA")
    vehicles = ", ".join(item.car_listing.title for item in order.items)
    payment_note = "Pay Now (pending confirmation)" if order.payment_method == "pay_now" else "Pay on Delivery"

    message = (
        f"🚗 New order — {order.order_number}\n"
        f"{vehicles}\n"
        f"Total: {order.total_amount:,.0f} {currency}\n"
        f"Payment: {payment_note}\n"
        f"Customer: {order.customer.full_name} — {order.customer.phone}\n"
        f"Fulfillment: {order.fulfillment_type.title()}"
        + (f" to {order.shipping_address}, {order.shipping_city}" if order.fulfillment_type == "delivery" and order.shipping_address else "")
    )
    return send_whatsapp_alert(message)


def notify_payment_received(order, amount, method):
    currency = os.environ.get("CURRENCY_SYMBOL", "CFA")
    status_line = "✅ FULLY PAID — marked as SOLD" if order.status == "paid" else f"Partial payment — balance {order.balance_due:,.0f} {currency} remaining"

    message = (
        f"💰 Payment received — {order.order_number}\n"
        f"Amount: {amount:,.0f} {currency} ({method.replace('_', ' ').title()})\n"
        f"{status_line}\n"
        f"Customer: {order.customer.full_name} — {order.customer.phone}"
    )
    return send_whatsapp_alert(message)
