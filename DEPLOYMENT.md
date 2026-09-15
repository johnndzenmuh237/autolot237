# Deployment Guide — LedgerIQ Business Management Dashboard

This guide walks through four ways to run LedgerIQ, from quickest to most
production-grade:

1. [Local development](#1-local-development)
2. [Docker (recommended for most people)](#2-docker-recommended)
3. [A real server: Ubuntu VPS with Gunicorn + Nginx + systemd](#3-ubuntu-vps-gunicorn--nginx--systemd)
4. [One-click PaaS hosting (Render / Railway)](#4-paas-hosting-render--railway)

Pick whichever fits how you want to run the app. Docker is the easiest way
to get something production-shaped without babysitting a server by hand.

---

## 1. Local Development

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
# The .env file is already provided with sane defaults — edit SECRET_KEY
# before you do anything real with it.
nano .env

# 4. Run the app (this also creates instance/business.db automatically)
python wsgi.py
```

Visit **http://localhost:5000**. A default admin (`admin` / `admin123`) is
created automatically on first run — change this immediately:

```bash
python scripts/create_admin.py
```

Optional demo data:

```bash
python scripts/seed_data.py
```

---

## 2. Docker (Recommended)

The project ships with a `Dockerfile` and `docker-compose.yml` that run the
app behind Gunicorn on port 8000.

### Step-by-step

```bash
# 1. Make sure Docker and Docker Compose are installed
docker --version
docker compose version

# 2. Edit .env — set a real SECRET_KEY at minimum
nano .env

# 3. Build and start the container
docker compose up -d --build

# 4. Check it's running
docker compose ps
docker compose logs -f web
```

Visit **http://localhost:8000**.

### Creating the admin account inside the container

```bash
docker compose exec web python scripts/create_admin.py
```

### Persisting data

`docker-compose.yml` mounts `./instance` into the container, so your SQLite
database (`business.db`) survives container restarts and rebuilds. For real
multi-user production use, switch to PostgreSQL instead (see below).

### Updating the app

```bash
git pull                     # or copy in your updated files
docker compose up -d --build
```

### Stopping

```bash
docker compose down
```

---

## 3. Ubuntu VPS: Gunicorn + Nginx + systemd

This is the classic "put it on a real server" path — works on a $5–6/mo VPS
(DigitalOcean, Linode, Hetzner, a home server, etc.). Assumes Ubuntu 22.04+.

### Step 1 — Server prep

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip nginx git
```

### Step 2 — Get the code onto the server

```bash
sudo mkdir -p /var/www/business-management-dashboard
sudo chown $USER:$USER /var/www/business-management-dashboard
cd /var/www/business-management-dashboard
# Copy your project files here (scp, git clone, rsync — whatever you use)
```

### Step 3 — Python environment

```bash
cd /var/www/business-management-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4 — Configure environment

```bash
nano .env
```

At minimum, set:

```
SECRET_KEY=<generate something long and random>
DATABASE_URL=sqlite:////var/www/business-management-dashboard/instance/business.db
FLASK_ENV=production
```

Generate a strong key quickly with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 5 — Initialize the database and admin account

```bash
mkdir -p instance
python -c "from app import create_app; create_app()"   # creates tables + default admin
python scripts/create_admin.py                          # set a real password
deactivate
```

### Step 6 — Set up the systemd service

A ready-made unit file is at `deploy/ledgeriq.service`. Copy it in and edit
the paths/user if yours differ from `/var/www/business-management-dashboard`
and `www-data`:

```bash
sudo mkdir -p /var/log/ledgeriq
sudo chown www-data:www-data /var/log/ledgeriq
sudo cp deploy/ledgeriq.service /etc/systemd/system/ledgeriq.service
sudo chown -R www-data:www-data /var/www/business-management-dashboard

sudo systemctl daemon-reload
sudo systemctl enable ledgeriq
sudo systemctl start ledgeriq
sudo systemctl status ledgeriq
```

Gunicorn is now listening on `127.0.0.1:8000` internally.

### Step 7 — Nginx reverse proxy

A ready-made config is at `deploy/nginx.conf`. Copy it in, set your domain,
and enable it:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ledgeriq
sudo nano /etc/nginx/sites-available/ledgeriq   # set server_name to your domain

sudo ln -s /etc/nginx/sites-available/ledgeriq /etc/nginx/sites-enabled/
sudo nginx -t          # test config
sudo systemctl reload nginx
```

Visit `http://your-domain.com` — you should see the login page.

### Step 8 — HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot edits the Nginx config to add a 443 (HTTPS) block and sets up
auto-renewal. Confirm renewal works with:

```bash
sudo certbot renew --dry-run
```

### Step 9 — Firewall (optional but recommended)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Updating the app later

```bash
cd /var/www/business-management-dashboard
git pull   # or copy in new files
source venv/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart ledgeriq
```

### Useful commands

```bash
sudo systemctl status ledgeriq      # is it running?
sudo journalctl -u ledgeriq -f      # live app logs
tail -f /var/log/ledgeriq/error.log # gunicorn error log
sudo systemctl restart ledgeriq     # restart after changes
```

---

## 4. PaaS Hosting (Render / Railway)

If you don't want to manage a server at all, both Render and Railway can
run this app directly from a Gunicorn start command with almost no config.

### Render

1. Push the project to a GitHub repository.
2. In Render, choose **New → Web Service** and connect the repo.
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 3 -b 0.0.0.0:$PORT --preload wsgi:app`
4. Add environment variables from your `.env` (`SECRET_KEY`, `DATABASE_URL`,
   `CURRENCY_SYMBOL`) in the Render dashboard's **Environment** tab.
5. For persistent storage of SQLite across deploys, attach a Render **Disk**
   mounted at `/opt/render/project/src/instance` — or better, use Render's
   managed PostgreSQL and point `DATABASE_URL` at it (see below).
6. Deploy. Render gives you a `https://your-app.onrender.com` URL with HTTPS
   already handled.

### Railway

1. Push the project to GitHub, then **New Project → Deploy from GitHub repo**
   in Railway.
2. Railway auto-detects Python; if it doesn't pick up the start command,
   set it explicitly in **Settings → Deploy**:
   `gunicorn -w 3 -b 0.0.0.0:$PORT --preload wsgi:app`
3. Add the same environment variables under **Variables**.
4. Optionally add Railway's managed PostgreSQL plugin and set `DATABASE_URL`
   to the connection string it provides.
5. Deploy — Railway gives you a public HTTPS URL automatically.

---

## Switching from SQLite to PostgreSQL (any deployment path)

SQLite is fine for a single small shop or for testing. For multiple
concurrent sellers hitting the app at once, PostgreSQL is safer:

```bash
pip install psycopg2-binary
```

Update `.env`:

```
DATABASE_URL=postgresql://username:password@host:5432/dbname
```

Nothing else changes — SQLAlchemy handles the rest. Restart the app after
updating `DATABASE_URL`.

---

## Production Checklist

- [ ] `SECRET_KEY` is a long random value, not the default
- [ ] Default admin password (`admin123`) has been changed
- [ ] `DATABASE_URL` points to PostgreSQL if more than one seller uses the
      app at the same time
- [ ] HTTPS is enabled (Certbot on your own server, or automatic on
      Render/Railway)
- [ ] Regular database backups are configured (`pg_dump` cron job, or your
      PaaS provider's backup feature)
- [ ] `FLASK_ENV=production` is set (disables debug mode)
- [ ] Server firewall only exposes ports 80/443 (and 22 for SSH)
