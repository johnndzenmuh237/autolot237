"""Seed the database with demo car listings for the storefront.

Usage:
    python scripts/seed_cars.py

Note: this only affects the database on the machine you run it on. If your
site is deployed (Render, etc.), running this locally does NOT seed your
live production database — use the "Seed Demo Cars" button in
Admin -> Storefront -> Car Listings instead, which runs this same logic
directly against whichever database your live app is actually using.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.utils.demo_data import seed_demo_cars  # noqa: E402


def run():
    app = create_app()
    with app.app_context():
        added, skipped = seed_demo_cars()
        print(f"Added {added} new car(s), skipped {skipped} already present.")
        print("Done.")


if __name__ == "__main__":
    run()
