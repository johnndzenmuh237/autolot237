"""Shared registration logic for managers, sellers and workers."""
import io
from datetime import datetime, date
from app import db
from app.models.user import User
from app.models.profile import UserProfile

MAX_PHOTO = 4 * 1024 * 1024
MAX_DOC = 3 * 1024 * 1024
ID_TYPES = ["National ID card (CNI)", "Passport", "Driver's licence", "Residence permit", "Other"]
EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Commission-based", "Internship"]
GENDERS = ["Male", "Female", "Other"]
MANAGER_DEPARTMENTS = ["Management", "Operations", "Sales", "Finance", "Inventory", "Customer Service"]
STAFF_DEPARTMENTS = ["Sales", "Operations", "Inventory", "Customer Service", "Workshop", "Administration"]
ACCESS_LEVELS = ["Standard manager", "Senior manager"]

# which fields are required for each kind of person
REQUIRED = {
    "manager": ["first_name", "last_name", "date_of_birth", "gender", "nationality", "email", "phone", "address", "city",
                "country", "national_id", "id_type", "position", "department", "employment_type", "hire_date", "username"],
    "seller": ["first_name", "last_name", "date_of_birth", "gender", "phone", "address", "city", "national_id",
               "position", "employment_type", "hire_date", "emergency_contact_name", "emergency_contact_phone", "username"],
    "worker": ["first_name", "last_name", "date_of_birth", "gender", "phone", "address", "city", "national_id",
               "position", "employment_type", "hire_date", "emergency_contact_name", "emergency_contact_phone", "username"],
}
LABELS = {
    "first_name": "First name", "last_name": "Last name", "date_of_birth": "Date of birth", "gender": "Gender",
    "nationality": "Nationality", "email": "Email address", "phone": "Primary phone number",
    "address": "Residential address", "city": "City", "country": "Country", "national_id": "ID number",
    "id_type": "ID type", "position": "Job title", "department": "Department", "employment_type": "Employment type",
    "hire_date": "Date of employment", "username": "Username", "emergency_contact_name": "Emergency contact name",
    "emergency_contact_phone": "Emergency contact phone",
}


def _date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return "bad"


def _float(value):
    try:
        v = float(value)
        return v if v >= 0 else "bad"
    except (TypeError, ValueError):
        return "bad"


def process_photo(file_storage):
    """Return (bytes, mime, error). Resizes to a small JPEG so it stays light."""
    data = file_storage.read()
    if not data:
        return None, None, None
    if len(data) > MAX_PHOTO:
        return None, None, "Profile photo must be smaller than 4 MB."
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((480, 480))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=85, optimize=True)
        return out.getvalue(), "image/jpeg", None
    except Exception:
        return None, None, "The profile photo is not a valid image (use JPG, PNG or WEBP)."


def process_id_document(file_storage):
    data = file_storage.read()
    if not data:
        return None, None, None, None
    if len(data) > MAX_DOC:
        return None, None, None, "ID document must be smaller than 3 MB."
    if data[:4] == b"%PDF":
        mime = "application/pdf"
    elif data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    else:
        return None, None, None, "ID document must be a PDF, JPG or PNG file."
    return data, mime, (file_storage.filename or "id-document")[:160], None


def parse_person(form, files, kind, password_required=True):
    """Validate a registration form. Returns (data, errors, uploads)."""
    f = {k: (v or "").strip() for k, v in form.items() if k not in ("password", "confirm_password", "csrf_token")}
    errors = []
    for key in REQUIRED[kind]:
        if not f.get(key):
            errors.append(f"{LABELS[key]} is required.")

    dob = _date(f.get("date_of_birth"))
    hire = _date(f.get("hire_date"))
    if dob == "bad" or hire == "bad":
        errors.append("Please enter valid dates.")
        dob = hire = None
    if dob and (date.today() - dob).days < 18 * 365:
        errors.append("The person must be at least 18 years old.")
    if hire and hire > date.today().replace(year=date.today().year + 1):
        errors.append("Date of employment is too far in the future.")

    if f.get("email") and ("@" not in f["email"] or "." not in f["email"].split("@")[-1]):
        errors.append("Please enter a valid email address.")
    if f.get("email") and User.query.filter_by(email=f["email"]).first():
        errors.append("That email address is already registered.")
    if f.get("username") and User.query.filter_by(username=f["username"]).first():
        errors.append("That username is already taken.")

    numbers = {}
    for key, label in (("salary", "Salary"), ("sales_target", "Sales target"), ("commission_rate", "Commission rate")):
        if f.get(key):
            v = _float(f[key])
            if v == "bad":
                errors.append(f"{label} must be a positive number.")
            else:
                numbers[key] = v
    if numbers.get("commission_rate", 0) > 100:
        errors.append("Commission rate cannot be more than 100%.")

    password, confirm = form.get("password", ""), form.get("confirm_password", "")
    if password_required or password:
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("The two passwords do not match.")

    uploads = {}
    photo = files.get("photo")
    if photo and photo.filename:
        b, m, err = process_photo(photo)
        errors.append(err) if err else uploads.update(photo=b, photo_mime=m)
    doc = files.get("id_document")
    if doc and doc.filename:
        b, m, n, err = process_id_document(doc)
        errors.append(err) if err else uploads.update(id_document=b, id_doc_mime=m, id_doc_name=n)

    f["_dob"], f["_hire"], f["_numbers"] = dob, hire, numbers
    f["_assigned"] = ",".join(x for x in form.getlist("assigned_products") if x.isdigit())
    return f, errors, uploads


def create_person(f, uploads, password, role, status_active=True):
    middle = f.get("middle_name", "")
    full = " ".join(p for p in (f["first_name"], middle, f["last_name"]) if p)
    user = User(
        full_name=full, username=f["username"], email=f.get("email") or None, role=role,
        position=f.get("position") or None, phone=f.get("phone"), address=f.get("address"),
        national_id=f.get("national_id") or None, city=f.get("city") or None,
        nationality=f.get("nationality") or None, gender=f.get("gender") or None,
        qualification=(f.get("qualification") or None), date_of_birth=f["_dob"], hire_date=f["_hire"],
        salary=f["_numbers"].get("salary", 0.0),
        emergency_contact_name=f.get("emergency_contact_name") or None,
        emergency_contact_phone=f.get("emergency_contact_phone") or None,
        notes=f.get("notes") or None, is_active_account=status_active,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    p = UserProfile(
        user_id=user.id, middle_name=middle or None, alt_phone=f.get("alt_phone") or None,
        country=f.get("country") or None, id_type=f.get("id_type") or None,
        department=f.get("department") or None, employment_type=f.get("employment_type") or None,
        experience=f.get("experience") or None, skills=f.get("skills") or None,
        responsibilities=f.get("responsibilities") or None, access_level=f.get("access_level") or None,
        sales_target=f["_numbers"].get("sales_target"), commission_rate=f["_numbers"].get("commission_rate"),
        assigned_products=f.get("_assigned") or None, **uploads,
    )
    db.session.add(p)
    db.session.commit()
    return user
