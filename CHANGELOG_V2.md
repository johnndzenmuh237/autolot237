# AutoLot237 v2 — what changed

This update layers three things onto the v1 storefront:
1. A full visual reskin of both the storefront **and** the LedgerIQ dashboard
   to match the LuxeShop design system you provided (navy `#1a1a2e` +
   crimson `#e94560`, Playfair Display headlines, Inter body copy).
2. Separate admin and seller logins.
3. A real payment workflow: Pay Now (full or partial) vs Pay on Delivery,
   with balance tracking on both staff dashboards and the customer's own
   account.

## Logins

- **Admin:** `/login` — rejects seller credentials with a message pointing
  to the seller login.
- **Seller:** `/seller-login` — rejects admin credentials the same way.
- **Staff portal chooser:** `/staff` — a simple page linking to both, if you
  want one link to hand out instead of two.
- **Customer account:** `/account/login` and `/account/signup` — separate
  from staff logins entirely (session-based, not tied to Flask-Login).
  Customers only get an account if they set a password at checkout, or
  sign up afterward — checkout still works as a guest either way.

Demo credentials (same as before): admin `admin` / `admin123`; seller
`john` / `seller123` (create this one from Admin → Employees if it's not
already in your database).

## Seller dashboard

Sellers now see:
- **Record a Sale** — unchanged, for walk-in/in-store sales only.
- **Website Orders** (new) — every online order, shared with the admin
  dashboard, showing the buyer's contact details, shipping address (if
  delivery was chosen), fulfillment type, and payment status/balance.
  Sellers can record a payment here (e.g. cash collected on delivery),
  but can't touch car listings or the leads inbox — those stay admin-only.

## Payment workflow

At checkout, the buyer picks:
- **Pay Now** — redirected to a generated invoice page with payment
  instructions (Mobile Money / bank transfer) and two buttons: pay the
  full balance, or pay half now. They can also type a custom amount.
  Clicking "I've Sent the Payment" self-confirms the payment immediately
  (see the honesty note below), updates their balance, and — once the
  full amount is in — automatically creates a real `Sale` record that
  shows up on both dashboards' Sales/Analytics.
- **Pay on Delivery** — the order is placed and the car is reserved
  (stock decrements immediately so it can't be double-sold), but nothing
  is marked paid or sold until someone actually collects the money.
  Staff (admin or seller) records that payment from the order's page on
  the Website Orders list, which then creates the Sale the same way.

**Partial payments** are fully supported: every payment is logged
individually, the order shows `Partially Paid` with a running balance
until it's settled, and that balance is visible on both the staff order
view and the customer's own `/account` dashboard.

### Honest limitation: no live payment gateway

There's still no real Mobile Money/card processor wired in (no merchant
credentials were provided). "Pay Now" is a **self-declared** confirmation
— the customer states they've sent the money, and it's marked accordingly
immediately, without a bank actually verifying the transfer. Every payment
is visible and auditable on the Website Orders page, so staff can catch
and correct anything that doesn't reconcile. Plugging in a real gateway
(MTN MoMo API, Orange Money API, Flutterwave, etc.) later would replace
just the "I've Sent the Payment" step with a real API call — the rest of
the order/balance/Sale logic doesn't need to change.

## Design

- `app/static/css/store.css` was rewritten to match the LuxeShop palette,
  type, and component patterns (header, ticker, product cards, buttons,
  forms) — same visual language as the sample you sent, adapted for cars.
- `app/static/css/main.css` (the dashboard's design tokens) was retargeted
  to the same navy/crimson/Playfair system. Because every dashboard page
  already used CSS variables instead of hardcoded colors, this one edit
  reskins the entire dashboard — sidebar, buttons, tables, cards, login —
  consistently, without touching any page's structure or risking broken
  functionality.
