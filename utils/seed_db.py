import os
import json
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from postgres.models import Base
import postgres.crud as pg_crud

def main():
    print("Loading environment variables...")
    load_dotenv()
    
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "password")
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = os.getenv("PG_PORT", "5432")
    PG_DB = os.getenv("PG_DB", "postgres")

    print("Connecting to PostgreSQL...")
    encoded_pwd = urllib.parse.quote_plus(PG_PASSWORD)
    DATABASE_URL = f"postgresql://{PG_USER}:{encoded_pwd}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    print("Reading JSON data...")
    with open("sd_restaurants.json", "r", encoding="utf-8") as f:
        restaurants = json.load(f)
        
    print(f"Found {len(restaurants)} restaurants. Beginning seed process...")
    
    for i, r in enumerate(restaurants):
        place_id = r.get("id")
        name = r.get("displayName", {}).get("text", "Unknown")
        primary_type = r.get("primaryType", "Unknown")
        lat = r.get("location", {}).get("latitude")
        lng = r.get("location", {}).get("longitude")
        location_wkt = f"POINT({lng} {lat})" if lat is not None and lng is not None else None
        
        rating = r.get("rating", 0.0)
        
        # Calculate min and max price
        min_price = None
        max_price = None
        if "priceRange" in r:
            try:
                min_price = float(r["priceRange"].get("startPrice", {}).get("units", 0))
                max_price = float(r["priceRange"].get("endPrice", {}).get("units", 0))
            except:
                pass
                
        access = r.get("accessibilityOptions", {})
        wheelchair_accessible = access.get("wheelchairAccessibleEntrance", False) or access.get("wheelchairAccessibleSeating", False)
        
        opening_hours = r.get("regularOpeningHours", {})
        
        # 1. PostgreSQL Create or Update
        existing = pg_crud.get_restaurant(db, place_id)
        if not existing:
            pg_crud.create_restaurant(
                db=db,
                place_id=place_id,
                location=location_wkt,
                rating=rating,
                min_price=min_price,
                max_price=max_price,
                wheelchair_accessible=wheelchair_accessible,
                opening_hours=opening_hours,
                google_maps_uri=r.get("googleMapsUri"),
                types=r.get("types", []),
                display_name=name,
                primary_type=primary_type
            )
        else:
            pg_crud.update_restaurant(
                db=db,
                place_id=place_id,
                google_maps_uri=r.get("googleMapsUri"),
                types=r.get("types", []),
                display_name=name,
                primary_type=primary_type
            )
            
        # 2. Neo4j Create
        # (Removed: Neo4j syncing is exclusively handled by sync_to_neo4j.py)
        
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} / {len(restaurants)} restaurants.")

    print(f"Finished processing all {len(restaurants)} restaurants.")
    db.close()

if __name__ == "__main__":
    main()
