import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "password")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "postgres")

encoded_pwd = urllib.parse.quote_plus(PG_PASSWORD)
DATABASE_URL = f"postgresql://{PG_USER}:{encoded_pwd}@{PG_HOST}:{PG_PORT}/{PG_DB}"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE restaurants ADD COLUMN google_maps_uri VARCHAR(500);"))
        print("Added google_maps_uri.")
    except Exception as e:
        print(f"Error google_maps_uri: {e}")
    
    try:
        conn.execute(text("ALTER TABLE restaurants ADD COLUMN types VARCHAR[];"))
        print("Added types.")
    except Exception as e:
        print(f"Error types: {e}")

    try:
        conn.execute(text("ALTER TABLE restaurants ADD COLUMN display_name VARCHAR(255);"))
        print("Added display_name.")
    except Exception as e:
        print(f"Error display_name: {e}")

    try:
        conn.execute(text("ALTER TABLE restaurants ADD COLUMN primary_type VARCHAR(255);"))
        print("Added primary_type.")
    except Exception as e:
        print(f"Error primary_type: {e}")
    
    conn.commit()
print("Migration script finished.")
