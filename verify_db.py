import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import urllib.parse
from dotenv import load_dotenv

from postgres.models import Restaurant
from neo4j_utils.crud import Neo4jConnector

load_dotenv()

PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "password")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "postgres")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

encoded_pwd = urllib.parse.quote_plus(PG_PASSWORD)
DATABASE_URL = f"postgresql://{PG_USER}:{encoded_pwd}@{PG_HOST}:{PG_PORT}/{PG_DB}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()
pg_count = db.query(Restaurant).count()
print(f"PostgreSQL Restaurants Count: {pg_count}")
db.close()

neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
try:
    with neo4j_conn.driver.session() as session:
        result = session.run("MATCH (n:Restaurant) RETURN count(n) as node_count")
        n_count = result.single()["node_count"]
        print(f"Neo4j Restaurants Node Count: {n_count}")
        
        c_result = session.run("MATCH (c:Cuisine) RETURN count(c) as cuisine_count")
        c_count = c_result.single()["cuisine_count"]
        print(f"Neo4j Cuisines Node Count: {c_count}")
        
        rel_result = session.run("MATCH (r:Restaurant)-[:SERVES]->(c:Cuisine) RETURN count(r) as rel_count")
        rel_count = rel_result.single()["rel_count"]
        print(f"Neo4j SERVES Relationships Count: {rel_count}")
finally:
    neo4j_conn.close()
