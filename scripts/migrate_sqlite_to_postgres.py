"""Copy all data from the local SQLite file into the database in DATABASE_URL.

Usage (from the project folder, with your Neon string in .env or exported):
    python scripts/migrate_sqlite_to_postgres.py [path/to/business.db]

WARNING: this EMPTIES the target tables first, then copies everything over.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, MetaData, text

src_path = sys.argv[1] if len(sys.argv) > 1 else "instance/business.db"
if not os.path.exists(src_path):
    sys.exit(f"Source database not found: {src_path}")

from dotenv import load_dotenv
load_dotenv()
dst_url = os.environ.get("DATABASE_URL", "").strip()
if not dst_url:
    sys.exit("DATABASE_URL is empty. Put your Neon connection string in .env first.")
if dst_url.startswith("postgres://"):
    dst_url = dst_url.replace("postgres://", "postgresql+psycopg://", 1)
elif dst_url.startswith("postgresql://"):
    dst_url = dst_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Make sure the tables exist on the target
os.environ["DATABASE_URL"] = dst_url
from app import create_app, db
app = create_app()

src = create_engine(f"sqlite:///{os.path.abspath(src_path)}")
dst = db.engine
src_meta = MetaData(); src_meta.reflect(bind=src)
dst_meta = MetaData(); dst_meta.reflect(bind=dst)

tables = [t for t in dst_meta.sorted_tables if t.name in src_meta.tables and t.name != "alembic_version"]

with src.connect() as s, dst.begin() as d:
    for t in reversed(tables):                      # empty children first
        d.execute(t.delete())
    for t in tables:                                # fill parents first
        cols = {c.name for c in t.columns}
        rows = [{k: v for k, v in r._mapping.items() if k in cols}
                for r in s.execute(src_meta.tables[t.name].select())]
        if rows:
            d.execute(t.insert(), rows)
        print(f"{t.name}: {len(rows)} rows")
    if dst.dialect.name == "postgresql":            # fix auto-increment counters
        for t in tables:
            if "id" in t.c:
                d.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{t.name}','id'), "
                    f"COALESCE((SELECT MAX(id) FROM {t.name}), 1))"))
print("Done.")
