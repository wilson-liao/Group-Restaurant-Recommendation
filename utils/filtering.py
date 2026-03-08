from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.types import Geography
from postgres.models import Restaurant, SessionMember
from postgres.crud import get_dining_session

def get_filtered_restaurants_for_session(db: Session, session_id):
    session = get_dining_session(db, session_id)
    if not session:
        return []

    # Start with base query
    query = db.query(Restaurant)

    # 1. Filter by Wheelchair Accessibility
    if session.requires_wheelchair:
        query = query.filter(Restaurant.wheelchair_accessible == True)

    # 2. Filter by Price Range
    # Assume session.max_price_level holds the group's max price
    if session.max_price_level is not None:
        query = query.filter(session.max_price_level >= Restaurant.max_price)

    # 3. Filter by Location Radius
    members = db.query(SessionMember).filter(SessionMember.session_id == session_id).all()
    for member in members:
        # Extract the WKT for safe geography casting in the query
        starting_wkt = db.scalar(func.ST_AsText(member.starting_location))
        if starting_wkt and member.max_travel_radius:
            query = query.filter(
                func.ST_DWithin(
                    func.cast(Restaurant.location, Geography),
                    func.cast(func.ST_GeomFromText(starting_wkt, 4326), Geography),
                    member.max_travel_radius
                )
            )

    restaurants = query.all()

    # 3. Filter by Dining Time (in Python because opening_hours is JSONB and complex)
    valid_restaurants = []
    if session.target_dining_time:
        target_time = session.target_dining_time
        target_day = (target_time.weekday() + 1) % 7 # Python: 0=Mon. Google Places: 0=Sun.
        target_time_val = target_time.hour * 60 + target_time.minute

        for r in restaurants:
            if not r.opening_hours or "periods" not in r.opening_hours:
                # If we don't know the hours, assume it's open to not be overly restrictive
                valid_restaurants.append(r)
                continue

            is_open = False
            for period in r.opening_hours["periods"]:
                open_data = period.get("open", {})
                close_data = period.get("close", {})

                open_day = open_data.get("day")
                
                # Check for 24-hour places (day 0, time 0000, no close)
                if open_day == 0 and not close_data:
                    is_open = True
                    break

                if open_day == target_day:
                    open_time = open_data.get("hour", 0) * 60 + open_data.get("minute", 0)
                    close_time = close_data.get("hour", 0) * 60 + close_data.get("minute", 0)

                    if close_time < open_time: # e.g. closes next day morning
                        if target_time_val >= open_time or target_time_val <= close_time:
                            is_open = True
                            break
                    else:
                        if open_time <= target_time_val <= close_time:
                            is_open = True
                            break
            
            if is_open:
                valid_restaurants.append(r)
    else:
        valid_restaurants = restaurants

    return valid_restaurants

def filter_restaurants_by_neo4j(neo4j_conn, session_id: str, valid_restaurants: list):
    """
    Uses Neo4j to filter a list of valid restaurants from Postgres.
    Filters by the dietary restrictions of all users in the session.
    Also calculates a cuisine score for each restaurant based on session preferences.
    Returns a sorted list of dictionaries with restaurant details and their cuisine scores.
    """
    if not valid_restaurants:
        return []

    place_ids = [r.place_id for r in valid_restaurants]
    
    # Neo4j query:
    # 1. Match users in the session and their dietary restrictions.
    # 2. Filter restaurants that accommodate ALL of these restrictions.
    # 3. Match the session cuisine desires to calculate a score for the restaurant.
    query = """
    MATCH (s:Session {id: $session_id})<-[:JOINED]-(u:User)
    OPTIONAL MATCH (u)-[:HAS_RESTRICTION]->(d:DietaryRestriction)
    WITH s, collect(distinct d) as session_restrictions
    
    MATCH (r:Restaurant)
    WHERE r.place_id IN $place_ids
    // If a user has restrictions, the restaurant MUST accommodate them.
    // The previous all() logic threw exception if list contained nulls, so handle it:
    WITH s, r, [res in session_restrictions WHERE res IS NOT NULL] as valid_restrictions
    WHERE all(restriction in valid_restrictions WHERE (r)-[:ACCOMMODATES]->(restriction))
    
    // Optional: get cuisine score
    OPTIONAL MATCH (s)-[sc:DESIRES_CUISINE]->(c:Cuisine)<-[:SERVES]-(r)
    WITH r, coalesce(sum(sc.total_session_score), 0) as cuisine_score
    
    RETURN r.place_id as place_id, cuisine_score
    ORDER BY cuisine_score DESC
    """
    
    result = neo4j_conn._execute_read(query, session_id=session_id, place_ids=place_ids)
    
    # Map back to Postgres restaurant models
    place_id_to_score = {rec["place_id"]: rec["cuisine_score"] for rec in result}
    
    filtered_and_scored = []
    for r in valid_restaurants:
        if r.place_id in place_id_to_score:
            filtered_and_scored.append({
                "restaurant": r,
                "score": place_id_to_score[r.place_id]
            })
            
    # Sort by score descending
    filtered_and_scored.sort(key=lambda x: x["score"], reverse=True)
    return filtered_and_scored

