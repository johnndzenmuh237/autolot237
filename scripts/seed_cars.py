"""Seed the database with demo car listings for the storefront.

Usage:
    python scripts/seed_cars.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.car import CarListing  # noqa: E402
from app.utils.codes import unique_slug, next_listing_code  # noqa: E402

CARS = [
    # make, model, year, mileage, transmission, fuel, body, color, condition, price, featured, image
    ("Toyota", "Corolla", 2019, 42000, "automatic", "petrol", "sedan", "Pearl White", "used", 6800000, True,
     "https://images.unsplash.com/photo-1623869675184-5b3d3e59f8f6?w=900&q=80"),
    ("Toyota", "RAV4", 2021, 18000, "automatic", "petrol", "suv", "Graphite", "used", 13500000, True,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Hyundai", "Tucson", 2022, 9000, "automatic", "petrol", "suv", "Deep Blue", "used", 15200000, True,
     "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=900&q=80"),
    ("Kia", "Picanto", 2020, 31000, "manual", "petrol", "hatchback", "Signal Red", "used", 4900000, False,
     "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&q=80"),
    ("Nissan", "X-Trail", 2018, 61000, "automatic", "diesel", "suv", "Silver", "used", 8700000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Toyota", "Hilux", 2023, 4000, "manual", "diesel", "pickup", "Sand", "new", 21500000, True,
     "https://images.unsplash.com/photo-1594502184342-2e12f877aa73?w=900&q=80"),
    ("Honda", "Civic", 2017, 78000, "automatic", "petrol", "sedan", "Black", "used", 5600000, False,
     "https://images.unsplash.com/photo-1590362891991-f776e747a588?w=900&q=80"),
    ("Mercedes-Benz", "C200", 2020, 26000, "automatic", "petrol", "sedan", "Obsidian Black", "used", 19800000, True,
     "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=900&q=80"),
    ("Ford", "Ranger", 2021, 22000, "automatic", "diesel", "pickup", "Blue", "used", 16400000, False,
     "https://images.unsplash.com/photo-1571607388263-1044f9ea01dd?w=900&q=80"),
    ("Suzuki", "Swift", 2019, 39000, "manual", "petrol", "hatchback", "Yellow", "used", 4200000, False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=900&q=80"),

    # --- expanded lot: more makes, models, price points, body types ---
    ("Toyota", "Camry", 2020, 33000, "automatic", "petrol", "sedan", "Midnight Blue", "used", 11200000, False,
     "https://images.unsplash.com/photo-1623869675184-5b3d3e59f8f6?w=900&q=80"),
    ("Toyota", "Yaris", 2021, 15000, "automatic", "petrol", "hatchback", "White", "used", 6100000, False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=900&q=80"),
    ("Toyota", "Land Cruiser Prado", 2022, 12000, "automatic", "diesel", "suv", "Pearl White", "used", 34500000, True,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Toyota", "Fortuner", 2021, 28000, "automatic", "diesel", "suv", "Silver", "used", 22800000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Toyota", "Hiace", 2019, 55000, "manual", "diesel", "van", "White", "used", 12900000, False,
     "https://images.unsplash.com/photo-1571607388263-1044f9ea01dd?w=900&q=80"),
    ("Honda", "CR-V", 2020, 34000, "automatic", "petrol", "suv", "Gray", "used", 12700000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Honda", "Accord", 2019, 47000, "automatic", "petrol", "sedan", "Silver", "used", 8900000, False,
     "https://images.unsplash.com/photo-1590362891991-f776e747a588?w=900&q=80"),
    ("Honda", "Pilot", 2021, 21000, "automatic", "petrol", "suv", "Black", "used", 17600000, False,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Hyundai", "Elantra", 2020, 29000, "automatic", "petrol", "sedan", "White", "used", 7400000, False,
     "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=900&q=80"),
    ("Hyundai", "Santa Fe", 2021, 19000, "automatic", "diesel", "suv", "Copper", "used", 16900000, True,
     "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=900&q=80"),
    ("Hyundai", "Accent", 2018, 58000, "manual", "petrol", "sedan", "Silver", "used", 4600000, False,
     "https://images.unsplash.com/photo-1623869675184-5b3d3e59f8f6?w=900&q=80"),
    ("Hyundai", "i10", 2022, 6000, "automatic", "petrol", "hatchback", "Red", "new", 5900000, False,
     "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&q=80"),
    ("Kia", "Sportage", 2021, 24000, "automatic", "petrol", "suv", "Blue", "used", 14300000, False,
     "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=900&q=80"),
    ("Kia", "Rio", 2019, 41000, "manual", "petrol", "hatchback", "White", "used", 4700000, False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=900&q=80"),
    ("Kia", "Sorento", 2022, 10000, "automatic", "diesel", "suv", "Graphite", "used", 19900000, True,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Kia", "Seltos", 2021, 26000, "automatic", "petrol", "suv", "Orange", "used", 11800000, False,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Nissan", "Micra", 2018, 49000, "manual", "petrol", "hatchback", "Blue", "used", 3900000, False,
     "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&q=80"),
    ("Nissan", "Qashqai", 2020, 32000, "automatic", "petrol", "suv", "Black", "used", 12100000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Nissan", "Navara", 2021, 20000, "manual", "diesel", "pickup", "White", "used", 17200000, False,
     "https://images.unsplash.com/photo-1594502184342-2e12f877aa73?w=900&q=80"),
    ("Nissan", "Sentra", 2019, 44000, "automatic", "petrol", "sedan", "Gray", "used", 6300000, False,
     "https://images.unsplash.com/photo-1590362891991-f776e747a588?w=900&q=80"),
    ("Mercedes-Benz", "E200", 2021, 17000, "automatic", "petrol", "sedan", "Black", "used", 28500000, True,
     "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=900&q=80"),
    ("Mercedes-Benz", "GLC 300", 2022, 8000, "automatic", "petrol", "suv", "White", "used", 36700000, True,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Mercedes-Benz", "A200", 2020, 25000, "automatic", "petrol", "hatchback", "Silver", "used", 15400000, False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=900&q=80"),
    ("BMW", "320i", 2020, 23000, "automatic", "petrol", "sedan", "Alpine White", "used", 21900000, False,
     "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=900&q=80"),
    ("BMW", "X3", 2021, 16000, "automatic", "petrol", "suv", "Black Sapphire", "used", 29800000, True,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Volkswagen", "Golf", 2019, 37000, "automatic", "petrol", "hatchback", "Blue", "used", 9200000, False,
     "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&q=80"),
    ("Volkswagen", "Tiguan", 2021, 21000, "automatic", "petrol", "suv", "Gray", "used", 17800000, False,
     "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=900&q=80"),
    ("Peugeot", "208", 2020, 30000, "manual", "petrol", "hatchback", "Red", "used", 6900000, False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=900&q=80"),
    ("Peugeot", "3008", 2021, 19000, "automatic", "diesel", "suv", "White", "used", 15900000, False,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Mazda", "CX-5", 2020, 27000, "automatic", "petrol", "suv", "Soul Red", "used", 14900000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Mazda", "3", 2019, 40000, "automatic", "petrol", "sedan", "White", "used", 7100000, False,
     "https://images.unsplash.com/photo-1590362891991-f776e747a588?w=900&q=80"),
    ("Lexus", "RX350", 2021, 14000, "automatic", "petrol", "suv", "Pearl White", "used", 31500000, True,
     "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=900&q=80"),
    ("Chevrolet", "Spark", 2018, 46000, "manual", "petrol", "hatchback", "Orange", "used", 3400000, False,
     "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&q=80"),
    ("Mitsubishi", "Pajero", 2019, 52000, "automatic", "diesel", "suv", "Black", "used", 18700000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
    ("Mitsubishi", "L200", 2020, 33000, "manual", "diesel", "pickup", "Gray", "used", 15600000, False,
     "https://images.unsplash.com/photo-1594502184342-2e12f877aa73?w=900&q=80"),
    ("Ford", "Everest", 2022, 11000, "automatic", "diesel", "suv", "Blue", "used", 24300000, False,
     "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=900&q=80"),
    ("Ford", "Focus", 2018, 51000, "automatic", "petrol", "hatchback", "Gray", "used", 5300000, False,
     "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=900&q=80"),
    ("Toyota", "Sienna", 2020, 29000, "automatic", "petrol", "van", "Silver", "used", 16200000, False,
     "https://images.unsplash.com/photo-1571607388263-1044f9ea01dd?w=900&q=80"),
    ("Suzuki", "Vitara", 2021, 22000, "automatic", "petrol", "suv", "White", "used", 10800000, False,
     "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&q=80"),
]


def run():
    app = create_app()
    with app.app_context():
        for (make, model, year, mileage, trans, fuel, body, color, condition,
             price, featured, image) in CARS:

            title = f"{year} {make} {model}"
            existing = Product.query.filter_by(name=title).first()
            if existing:
                print(f"skip (exists): {title}")
                continue

            product = Product(
                name=title, category="Cars", sku=None,
                stock_quantity=1, cost_price=price * 0.85,
                min_price=price, max_price=price,
            )
            db.session.add(product)
            db.session.flush()

            listing = CarListing(
                product_id=product.id,
                slug=unique_slug(title, lambda s: CarListing.query.filter_by(slug=s).first() is not None),
                listing_code=next_listing_code(lambda c: CarListing.query.filter_by(listing_code=c).first() is not None),
                make=make, model=model, year=year, mileage_km=mileage,
                transmission=trans, fuel_type=fuel, body_type=body,
                exterior_color=color, condition=condition, location="Douala, Cameroon",
                description=f"Well-maintained {title} in {color.lower()}, inspected and ready for handover.",
                features_csv="Air conditioning, Power windows, Bluetooth, Reverse camera, Alloy wheels",
                main_image=image, is_featured=featured, is_published=True,
            )
            listing.set_gallery([image])
            db.session.add(listing)
            db.session.commit()
            print(f"added: {title} ({listing.listing_code})")

        print("Done.")


if __name__ == "__main__":
    run()
