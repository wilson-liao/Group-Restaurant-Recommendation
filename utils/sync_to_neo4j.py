import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import Models and utilities
from postgres.models import User, Restaurant
from neo4j_utils.crud import Neo4jConnector
from utils.dietary_classifier import get_dietary_restrictions_for_restaurant
from utils.cuisine_classifier import get_cuisines_for_restaurant

def main():
    # Load environment variables
    load_dotenv()
    
    print("Connecting to PostgreSQL...")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "password")
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = os.getenv("PG_PORT", "5432")
    PG_DB = os.getenv("PG_DB", "postgres")
    
    encoded_pwd = urllib.parse.quote_plus(PG_PASSWORD)
    DATABASE_URL = f"postgresql://{PG_USER}:{encoded_pwd}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    print("Connecting to Neo4j...")
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    print("Setting up Constraints in Neo4j...")
    constraints = [
        "CREATE CONSTRAINT unique_user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;",
        "CREATE CONSTRAINT unique_place_id IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.place_id IS UNIQUE;",
        "CREATE CONSTRAINT unique_dr_name IF NOT EXISTS FOR (d:DietaryRestriction) REQUIRE d.name IS UNIQUE;",
        "CREATE CONSTRAINT unique_cuisine_name IF NOT EXISTS FOR (c:Cuisine) REQUIRE c.name IS UNIQUE;"
    ]
    for q in constraints:
        neo4j_conn._execute_write(q)
        
    print("Fetching Users from PostgreSQL...")
    users = db.query(User).all()
    print(f"Found {len(users)} users.")
    for u in users:
        neo4j_conn.create_user(user_id=str(u.user_id), name=u.name)
        
    print("Fetching Restaurants from PostgreSQL...")
    restaurants = db.query(Restaurant).all()
    print(f"Found {len(restaurants)} restaurants.")

    for r in restaurants:
        r_name = r.display_name or "Unknown"
        neo4j_conn.create_restaurant(place_id=r.place_id, name=r_name)
        
        # Calculate categories
        restrictions = get_dietary_restrictions_for_restaurant(r_name, r.types)
        cuisines = get_cuisines_for_restaurant(r_name, r.types)
        if r_name == 'RAKITORI Japanese Pub&Grill':
            print(f'Found RAKITORI')
            print(cuisines)
        
        for res in restrictions:
            neo4j_conn.create_dietary_restriction(name=res)
            neo4j_conn.add_restaurant_accommodation(place_id=r.place_id, restriction_name=res)
            
        for cui in cuisines:
            neo4j_conn.create_cuisine(name=cui)
            neo4j_conn.add_restaurant_cuisine(place_id=r.place_id, cuisine_name=cui)
            
    print("Sync Complete! Data successfully populated in Neo4j.")
    
    db.close()
    neo4j_conn.close()

if __name__ == "__main__":
    main()
