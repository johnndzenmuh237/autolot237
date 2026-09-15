import re
import random
import string
from datetime import datetime


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def unique_slug(base_text, exists_fn):
    """exists_fn(candidate) -> bool. Appends -2, -3... until free."""
    base = slugify(base_text) or "car"
    candidate = base
    i = 2
    while exists_fn(candidate):
        candidate = f"{base}-{i}"
        i += 1
    return candidate


def next_listing_code(exists_fn, prefix="LT"):
    while True:
        candidate = f"{prefix}-{random.randint(100, 999)}"
        if not exists_fn(candidate):
            return candidate


def new_order_number():
    stamp = datetime.utcnow().strftime("%y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"AL-{stamp}-{suffix}"
