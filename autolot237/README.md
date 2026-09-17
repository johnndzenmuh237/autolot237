# LedgerIQ — Business Management Dashboard

A role-based business management dashboard for tracking inventory, sales, profit,
and employee performance — with a built-in AI business analyst that explains
what's happening in plain language.

## Features

- **Admin / Business Owner**: manage products, stock, costs, and pricing; view
  revenue, profit, expenses, and AI-generated insights.
- **Full employee records**: register staff with complete contact details
  (phone, address, national ID, emergency contact), position, and salary.
  Each employee has a full profile page showing their details, tenure,
  sales performance, and payroll history — none of this is visible to
  sellers.
- **Payroll tracking**: automatic monthly payment records generated from
  each employee's hire date. Manager ticks "Mark Paid" once salary is paid;
  it displays as Paid immediately and stays in the record permanently.
- **Tick-to-sell interface**: sellers see a read-only checklist of every
  product currently in stock — they cannot edit prices or inventory, only
  set quantity/price and tick a box to record a sale. Ticking updates stock
  and dashboards instantly via a background request, no page reload needed.
- **Automatic stock control**: sales reduce inventory in real time, with
  configurable low-stock alerts.
- **Daily / weekly / monthly analytics**: revenue, profit, top products, and
  category breakdowns.
- **AI Business Insights**: a rule-based analyst that reviews trends, margins,
  slow-moving stock, and seller performance, then explains it in plain English.
  No external API key required.
- **Expense tracking**: product purchases and other business expenses roll up
  into a net profit calculation.

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate, Flask-WTF
- **Database**: SQLite by default (swap `DATABASE_URL` for PostgreSQL in production)
- **Frontend**: Server-rendered Jinja templates, vanilla JS, Chart.js for graphs
- **Currency**: CFA Franc (XAF), configurable via `.env`

## Getting Started

For a full step-by-step deployment guide (local dev, Docker, a production
VPS with Gunicorn + Nginx + systemd, or one-click PaaS hosting), see
**[DEPLOYMENT.md](DEPLOYMENT.md)**. Quick local setup:

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env   # or edit the provided .env directly
# Set a real SECRET_KEY before deploying to production

# 4. Run the app (creates the SQLite database automatically)
python wsgi.py
```

The app will be available at **http://localhost:5000**.

On first run, a default admin account is created automatically:

```
username: admin
password: admin123
```

**Change this password immediately** via `scripts/create_admin.py`, or by
adding a "change password" flow before deploying.

> **Upgrading from an older version of this project?** The employee model
> now includes HR fields (phone, address, position, salary, hire date, etc.)
> and a new payroll table. If you have an existing `instance/business.db`
> from before this change, delete it and re-run the app (or re-seed) so the
> new columns are created — SQLite here doesn't auto-migrate schema changes.

### Optional: load demo data

```bash
python scripts/seed_data.py
```

This adds sample laptops/accessories, three demo sellers (`john`, `marie`,
`paul`, password `seller123`), and ~120 days of sample sales so you can see
the dashboard, charts, and AI insights populated immediately.

### Optional: reset/create an admin account

```bash
python scripts/create_admin.py
```

## Project Structure

See the file tree in this repository — it follows a standard Flask
application-factory layout:

- `app/models/` — SQLAlchemy models (User, Product, Sale, InventoryPurchase, Expense, AIInsight)
- `app/routes/` — Blueprints for auth, admin, seller, inventory, sales, analytics, expenses, ai
- `app/services/` — Business logic: stock control, sale validation, profit math, analytics queries, AI insight generation
- `app/utils/` — Currency formatting, role-based decorators, helpers
- `app/templates/` — Jinja templates split into `admin/`, `seller/`, and shared `components/`
- `app/static/` — CSS (one file per concern) and JS

## Roles & Permissions

- **Admin** can add/edit products, update stock, set pricing, view all sales,
  manage sellers, record expenses, and view AI insights.
- **Seller** can only select a product, enter quantity and price, and submit
  a sale within the admin-defined min/max price range. Everything else is
  read-only or automatic for sellers.

## Notes on the AI Insights Engine

`app/services/ai_service.py` implements a deterministic, rule-based analyst
that compares this month to last month, checks profit margins, flags slow
movers and low stock, and highlights top performers — all computed directly
from your own database, so it works offline and requires no API key. If you
want richer, model-generated language, you can extend `ai_service.py` to call
the Anthropic API (or any LLM) using the aggregated data it already computes,
and use that to rewrite the `message` fields before saving `AIInsight` rows.

## Production Checklist

- Set a strong, unique `SECRET_KEY` in `.env`
- Switch `DATABASE_URL` to PostgreSQL for concurrent multi-user use
- Put the app behind a WSGI server (gunicorn/uwsgi) and a reverse proxy
- Force HTTPS and set `SESSION_COOKIE_SECURE = True`
- Remove or change the default admin credentials before going live
