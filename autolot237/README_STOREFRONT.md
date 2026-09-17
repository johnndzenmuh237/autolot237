# AutoLot237 — Car Selling Storefront (built on your LedgerIQ dashboard)

This adds a public, SEO-optimized car dealership website in front of your
existing **business-management-dashboard** (LedgerIQ). It's the same Flask
app, same database, same login — nothing in your original dashboard code was
rewritten. New files were added, and three existing files got small,
additive edits (see "What was touched" below).

## What you get

- **Public storefront** at `/` — home, browse/filter cars, car detail pages,
  cart, checkout, order confirmation, PDF invoices.
- **Real checkout → real dashboard update.** When a customer buys a car
  online, it creates an `Order` *and* records a normal `Sale` (via your
  existing `record_sale()` service) under a system "Online Store" seller
  account — so it shows up in **Sales History**, **Analytics**, and **AI
  Insights** exactly like a sale entered manually. Stock decrements
  automatically.
- **AI customer support widget** — inventory-aware out of the box (no API
  key needed). Optionally set `ANTHROPIC_API_KEY` to route replies through
  Claude, still grounded only in your real stock.
- **WhatsApp** — a working "Chat on WhatsApp" button (wa.me click-to-chat)
  that logs every click as a lead first. A webhook route is stubbed out for
  the Meta/Twilio WhatsApp Business API if you want automated replies later
  (see below — this part needs your own API credentials, which I don't
  have).
- **CRM inbox** — every WhatsApp click, AI chat handoff, and test-drive
  request lands in **Admin → Storefront → Leads**.
- **Invoices** — instant branded PDF invoice per order, downloadable from
  the confirmation page and from the admin order view.
- **SEO** — per-page meta tags, Open Graph, JSON-LD (`Vehicle`/`AutoDealer`
  schema), `sitemap.xml`, `robots.txt`, clean slugged URLs.
- **Responsive** — mobile / tablet / desktop, tested down to 360px.

## What was touched in your existing code

Only three small, additive edits — nothing existing was removed or redesigned:
1. `app/__init__.py` — registers the two new blueprints (`store`, `store_admin`).
2. `app/models/__init__.py` — imports the four new models.
3. `app/templates/components/sidebar.html` — added one new nav group
   ("Storefront") linking to the new admin pages. Your existing nav items
   are unchanged.

Everything else (13 new Python files, 13 new templates, 2 new static
assets) lives alongside your current files and doesn't modify them.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your real values — see below
python scripts/seed_cars.py   # optional: adds 10 demo car listings
python wsgi.py   # or your usual gunicorn command
```

The app auto-creates tables on first run (same as before — nothing new to
migrate manually), and creates the default admin (`admin` / `admin123`) if
no users exist yet, exactly as it did before.

Visit `/` for the storefront and `/admin/store/cars` (while logged in as
admin) to add your real inventory — replace the demo photo URLs with your
own car photos.

## Environment variables that matter for the storefront

| Variable | What it does |
|---|---|
| `BUSINESS_NAME`, `BUSINESS_ADDRESS`, `BUSINESS_PHONE`, `BUSINESS_EMAIL`, `BUSINESS_HOURS` | Shown across the site, invoices, and AI assistant answers |
| `SITE_URL` | Used for canonical URLs, sitemap, and Open Graph tags |
| `WHATSAPP_NUMBER` | Enables the WhatsApp button (digits only, country code first, e.g. `237677123456`) |
| `ANTHROPIC_API_KEY` | Optional — upgrades the AI widget from rule-based to Claude, still grounded in your live stock |

## Honest limitations — what still needs your input

I built everything that can run without third-party credentials. Three
things are stubbed and clearly marked in the code because they need
accounts/keys I don't have access to:

1. **Real payment processing.** Checkout currently supports Mobile Money /
   Bank Transfer / Pay-at-showroom as *selected payment methods*, but there's
   no live payment gateway wired in — orders are marked "paid" or "awaiting
   payment" based on the method chosen, and your team confirms payment
   manually (same as most local dealerships do today). To take real Mobile
   Money or card payments automatically, you'd connect a provider like
   MTN MoMo API, Orange Money API, or a card processor such as Flutterwave —
   I can wire one in once you have merchant credentials.
2. **Automated WhatsApp replies.** Click-to-chat works right now with zero
   setup. Fully automated WhatsApp (auto-replies, message history, the AI
   answering directly *inside* WhatsApp) requires a Meta WhatsApp Business
   Cloud API account (or Twilio) — the webhook route at
   `/webhooks/whatsapp` is ready to receive messages once you add
   `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_VERIFY_TOKEN`.
3. **Real car photos.** Seed data uses stock photos from Unsplash as
   placeholders. Replace `gallery_urls` in each listing (Admin → Storefront →
   Car Listings → Edit) with your own photos once you have them hosted
   somewhere (S3, Cloudinary, or even just your own server's `/static/`
   folder).

Everything else — browsing, filtering, cart, checkout, invoicing, the sale
flowing into your dashboard, the AI chat, lead capture, and SEO — is fully
working end-to-end; I tested the whole purchase flow (add to cart → checkout
→ Sale created → stock decremented → Sales History updated → invoice PDF
generated) before packaging this.
