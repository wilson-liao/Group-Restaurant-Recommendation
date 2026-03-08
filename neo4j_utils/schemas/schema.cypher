// Constraints to ensure uniqueness and improve lookup performance
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT restaurant_place_id_unique IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.place_id IS UNIQUE;
CREATE CONSTRAINT dietary_restriction_name_unique IF NOT EXISTS FOR (d:DietaryRestriction) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT cuisine_name_unique IF NOT EXISTS FOR (c:Cuisine) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE;

// Indexes can also be created for fast lookups if not primary keys (e.g., name index)
CREATE INDEX user_name_idx IF NOT EXISTS FOR (u:User) ON (u.name);
CREATE INDEX restaurant_name_idx IF NOT EXISTS FOR (r:Restaurant) ON (r.name);
