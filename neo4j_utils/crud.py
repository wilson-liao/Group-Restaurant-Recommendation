from neo4j import GraphDatabase

class Neo4jConnector:
    """
    A unified wrapper for Neo4j database operations customized for graph storage and querying.
    """
    
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Closes the current database driver connection."""
        self.driver.close()

    def _execute_write(self, query, **kwargs):
        """Helper to run a write transaction query."""
        with self.driver.session() as session:
            result = session.run(query, **kwargs)
            return [record.data() for record in result]

    def _execute_read(self, query, **kwargs):
        """Helper to run a read transaction query."""
        with self.driver.session() as session:
            result = session.run(query, **kwargs)
            return [record.data() for record in result]

    # --- NODE CREATION ---
    
    def create_user(self, user_id: str, name: str):
        query = """
        MERGE (u:User {id: $user_id})
        SET u.name = $name
        RETURN u
        """
        return self._execute_write(query, user_id=user_id, name=name)

    def create_restaurant(self, place_id: str, name: str):
        query = """
        MERGE (r:Restaurant {place_id: $place_id})
        SET r.name = $name
        RETURN r
        """
        return self._execute_write(query, place_id=place_id, name=name)

    def create_dietary_restriction(self, name: str):
        query = """
        MERGE (d:DietaryRestriction {name: $name})
        RETURN d
        """
        return self._execute_write(query, name=name)

    def create_cuisine(self, name: str):
        query = """
        MERGE (c:Cuisine {name: $name})
        RETURN c
        """
        return self._execute_write(query, name=name)

    def create_session(self, session_id: str):
        query = """
        MERGE (s:Session {id: $session_id})
        RETURN s
        """
        return self._execute_write(query, session_id=session_id)

    # --- STATIC RELATIONSHIPS ---
    # Relationships that do not change based on user sessions

    def add_user_restriction(self, user_id: str, restriction_name: str):
        query = """
        MATCH (u:User {id: $user_id})
        MATCH (d:DietaryRestriction {name: $restriction_name})
        MERGE (u)-[r:HAS_RESTRICTION]->(d)
        RETURN count(r) as relationships_created
        """
        return self._execute_write(query, user_id=user_id, restriction_name=restriction_name)

    def add_restaurant_accommodation(self, place_id: str, restriction_name: str):
        query = """
        MATCH (r:Restaurant {place_id: $place_id})
        MATCH (d:DietaryRestriction {name: $restriction_name})
        MERGE (r)-[acc:ACCOMMODATES]->(d)
        RETURN count(acc) as relationships_created
        """
        return self._execute_write(query, place_id=place_id, restriction_name=restriction_name)

    def add_restaurant_cuisine(self, place_id: str, cuisine_name: str):
        query = """
        MATCH (r:Restaurant {place_id: $place_id})
        MATCH (c:Cuisine {name: $cuisine_name})
        MERGE (r)-[srv:SERVES]->(c)
        RETURN count(srv) as relationships_created
        """
        return self._execute_write(query, place_id=place_id, cuisine_name=cuisine_name)

    # --- DYNAMIC RELATIONSHIPS (Per-Session) ---
    
    def user_join_session(self, user_id: str, session_id: str):
        query = """
        MATCH (u:User {id: $user_id})
        MATCH (s:Session {id: $session_id})
        MERGE (u)-[j:JOINED]->(s)
        RETURN count(j) as relationships_created
        """
        return self._execute_write(query, user_id=user_id, session_id=session_id)

    def user_desires_cuisine(self, user_id: str, cuisine_name: str, session_id: str, score: int):
        """
        When a user creates or updates an active session, they write a temporary edge.
        """
        query = """
        MATCH (u:User {id: $user_id})
        MATCH (c:Cuisine {name: $cuisine_name})
        MERGE (u)-[rel:DESIRES_CUISINE {session_id: $session_id}]->(c)
        SET rel.score = $score
        RETURN count(rel) as relationships_created
        """
        return self._execute_write(query, user_id=user_id, cuisine_name=cuisine_name, session_id=session_id, score=score)

    def update_session_cuisine_score(self, session_id: str, cuisine_name: str):
        """
        Calculates score by summing up each session member's score from their [:DESIRES_CUISINE] edges 
        tied to that specific cuisine and attaches it to the Session directly for quick lookups.
        """
        query = """
        MATCH (u:User)-[rel:DESIRES_CUISINE {session_id: $session_id}]->(c:Cuisine {name: $cuisine_name})
        WITH sum(rel.score) as total_score, c
        MATCH (s:Session {id: $session_id})
        MERGE (s)-[s_rel:DESIRES_CUISINE]->(c)
        SET s_rel.score = total_score
        RETURN total_score
        """
        return self._execute_write(query, session_id=session_id, cuisine_name=cuisine_name)
    
    def add_user_to_neo4j(self, user_id: str, name: str, restrictions: list):
        """
        Inserts a new user and their dietary restrictions into Neo4j.
        """
        self.create_user(user_id=user_id, name=name)
        for res in restrictions:
            self.create_dietary_restriction(name=res)
            self.add_user_restriction(user_id=user_id, restriction_name=res)

    def add_session_data_to_neo4j(self, session_id: str, user_data: dict):
        """
        Inserts session relationships for users mapping to the session and their desired cuisines.
        user_data format: { "user_id": { "cuisines": {"Italian": 10, "Mexican": 5} } }
        """
        self.create_session(session_id=session_id)
        
        for uid_str, data in user_data.items():
            self.user_join_session(user_id=uid_str, session_id=session_id)
            
            if 'cuisines' in data:
                for cuisine_name, score in data['cuisines'].items():
                    self.create_cuisine(name=cuisine_name)
                    self.user_desires_cuisine(
                        user_id=uid_str, 
                        cuisine_name=cuisine_name, 
                        session_id=session_id, 
                        score=score
                    )
                    self.update_session_cuisine_score(
                        session_id=session_id,
                        cuisine_name=cuisine_name
                    )

    def delete_all_sessions(self):
        """
        Deletes all Session nodes and their connected relationships from Neo4j.
        """
        query = """
        MATCH (s:Session)
        DETACH DELETE s
        """
        return self._execute_write(query)

    # --- SOME USEFUL QUERIES ---
    def get_restaurants_accommodating_session(self, session_id: str):
        """
        Example query: Find all restaurants that accommodate the restrictions of ALL users currently in a session.
        """
        query = """
        MATCH (s:Session {id: $session_id})<-[:JOINED]-(u:User)-[:HAS_RESTRICTION]->(d:DietaryRestriction)
        WITH s, collect(distinct d) as session_restrictions
        MATCH (r:Restaurant)
        WHERE all(restriction in session_restrictions WHERE (r)-[:ACCOMMODATES]->(restriction))
        RETURN r.place_id as place_id, r.name as name
        """
        return self._execute_read(query, session_id=session_id)
