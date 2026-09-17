"""Create or reset the admin account.

Usage:
    python scripts/create_admin.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from app.models.user import User  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        username = input("Admin username [admin]: ").strip() or "admin"
        full_name = input("Full name [Business Owner]: ").strip() or "Business Owner"
        password = input("Password: ").strip()

        if not password:
            print("Password cannot be empty.")
            return

        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(password)
            user.role = "admin"
            print(f"Updated existing user '{username}' to admin with new password.")
        else:
            user = User(full_name=full_name, username=username, role="admin")
            user.set_password(password)
            db.session.add(user)
            print(f"Created new admin user '{username}'.")

        db.session.commit()


if __name__ == "__main__":
    main()
