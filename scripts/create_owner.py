"""Create (or reset) the Business Owner account.

    python scripts/create_owner.py

Uses the database in DATABASE_URL (.env). Asks for the password so it is
never stored in a file or shell history.
"""
import os, sys, getpass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    username = input("Owner username [owner]: ").strip() or "owner"
    name = input("Owner full name [Business Owner]: ").strip() or "Business Owner"
    pw = getpass.getpass("Password (8+ characters): ")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters.")
    u = User.query.filter_by(username=username).first()
    if u and u.role != "owner":
        sys.exit(f"'{username}' already exists as a {u.role}. Choose another username.")
    if not u:
        u = User(username=username, full_name=name, role="owner", position="Business Owner")
        db.session.add(u)
    u.set_password(pw); u.is_active_account = True
    db.session.commit()
    print(f"Owner account '{username}' is ready. Sign in at /login")
