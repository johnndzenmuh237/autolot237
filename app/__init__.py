import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.seller import seller_bp
    from app.routes.inventory import inventory_bp
    from app.routes.sales import sales_bp
    from app.routes.analytics import analytics_bp
    from app.routes.expenses import expenses_bp
    from app.routes.ai import ai_bp
    from app.routes.storefront import store_bp
    from app.routes.storefront_admin import store_admin_bp
    from app.routes.account import account_bp
    from app.routes.attendance import attendance_bp
    from app.routes.owner import owner_bp
    from app.routes.notifications import notifications_bp
    from app.routes.pwa import pwa_bp
    from app.routes.people import people_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(store_admin_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(pwa_bp)
    app.register_blueprint(people_bp)

    # The bell polls every 20s and the PWA files are fetched constantly:
    # keep them out of the 200/hour default rate limit.
    limiter.exempt(notifications_bp)
    limiter.exempt(pwa_bp)

    @app.before_request
    def enforce_active_account():
        """A deactivated account (e.g. a replaced manager) loses access at once,
        even if their browser still holds a 'remember me' cookie."""
        if request.endpoint and request.endpoint != "static" and current_user.is_authenticated \
                and not current_user.is_active_account:
            logout_user()
            flash("Your account has been deactivated. Contact the business owner.", "error")
            return redirect(url_for("auth.staff_portal"))

    # Only the true JSON/fetch API endpoints (called by JS, not an HTML form)
    # are CSRF-exempt — every real <form> on the storefront now carries a
    # CSRF token instead of the whole blueprint being exempt.
    csrf.exempt(store_bp.name + ".api_chat")
    csrf.exempt(store_bp.name + ".api_chat_handoff")
    csrf.exempt(store_bp.name + ".whatsapp_lead")
    csrf.exempt(store_bp.name + ".whatsapp_webhook")
    csrf.exempt(store_bp.name + ".car_lead")

    # Brute-force protection on the login pages and the payment-confirmation
    # endpoint (the only places an attacker gains by hammering repeatedly).
    limiter.limit("10 per minute")(auth_bp)
    limiter.limit("20 per minute")(store_bp)

    from app.utils.currency import format_currency
    app.jinja_env.filters["currency"] = format_currency

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        setup_open = False
        try:
            if current_user.is_authenticated and current_user.role == "admin":
                from app.utils.owner_setup import owner_setup_available
                setup_open = owner_setup_available()
        except Exception:
            setup_open = False
        return {
            "owner_setup_open": setup_open,
            "currency_symbol": app.config["CURRENCY_SYMBOL"],
            "current_user": current_user,
            "ga_measurement_id": app.config.get("GA_MEASUREMENT_ID", ""),
        }

    @app.after_request
    def set_security_headers(response):
        # Baseline hardening headers — cheap to add, meaningfully reduce
        # clickjacking, MIME-sniffing, and referrer-leak risk. This does NOT
        # replace HTTPS being enforced at the hosting/proxy layer (Render,
        # etc. terminate TLS for you) — see DEPLOYMENT.md.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not app.config["DEBUG"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(404)
    def not_found(e):
        # Store-branded 404 for public pages, dashboard-branded 404 for
        # /admin, /seller, /login and friends — so the error page always
        # matches the surface the visitor was actually on.
        staff_prefixes = ("/admin", "/seller", "/login", "/seller-login", "/staff", "/inventory", "/sales", "/analytics", "/expenses", "/ai")
        if request.path.startswith(staff_prefixes):
            return render_template("errors/404.html"), 404
        return render_template("store/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template("errors/429.html"), 429

    with app.app_context():
        try:
            db.create_all()
        except Exception:
            # Multiple worker processes booting simultaneously against a
            # brand-new SQLite file can race on table creation. Safe to
            # ignore here — whichever worker wins, the tables end up
            # created either way. Use `gunicorn --preload` in production
            # to avoid this race entirely (see DEPLOYMENT.md).
            db.session.rollback()
        from app.utils.db_upgrade import ensure_user_columns
        ensure_user_columns()
        from app.utils.helpers import ensure_default_admin
        ensure_default_admin()
        from app.utils.helpers import ensure_owner_account
        ensure_owner_account()

        # Gunicorn --preload forks workers AFTER this runs. A Postgres SSL
        # connection can't be shared across forked processes, so drop the
        # startup connection here and let each worker open its own.
        db.session.remove()
        db.engine.dispose()

    return app
