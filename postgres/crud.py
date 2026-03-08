from sqlalchemy.orm import Session
from sqlalchemy import or_
from .models import User, Restaurant, DiningSession, SessionMember

# --- USER CRUD ---

def create_user(db: Session, name: str):
    user = User(name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db: Session, user_id):
    return db.query(User).filter(User.user_id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id, name: str):
    user = get_user(db, user_id)
    if user:
        user.name = name
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id):
    user = get_user(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

# --- RESTAURANT CRUD ---

def create_restaurant(db: Session, place_id: str, location: str, rating: float = None, min_price: float = None, max_price: float = None, wheelchair_accessible: bool = None, opening_hours: dict = None):
    # Location should be passed as a WKT string, e.g., 'POINT(-71.060316 48.432044)'
    restaurant = Restaurant(
        place_id=place_id,
        location=location,
        rating=rating,
        min_price=min_price,
        max_price=max_price,
        wheelchair_accessible=wheelchair_accessible,
        opening_hours=opening_hours
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant

def get_restaurant(db: Session, place_id: str):
    return db.query(Restaurant).filter(Restaurant.place_id == place_id).first()

def get_restaurants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Restaurant).offset(skip).limit(limit).all()

def update_restaurant(db: Session, place_id: str, **kwargs):
    restaurant = get_restaurant(db, place_id)
    if restaurant:
        for key, value in kwargs.items():
            setattr(restaurant, key, value)
        db.commit()
        db.refresh(restaurant)
    return restaurant

def delete_restaurant(db: Session, place_id: str):
    restaurant = get_restaurant(db, place_id)
    if restaurant:
        db.delete(restaurant)
        db.commit()
        return True
    return False

# --- DINING SESSION CRUD ---

def create_dining_session(db: Session, creator_id, target_location: str, max_price_level: int = None, target_dining_time = None, requires_wheelchair: bool = None):
    # target_location should be a WKT string 'POINT(long lat)'
    session = DiningSession(
        creator_id=creator_id,
        target_location=target_location,
        max_price_level=max_price_level,
        target_dining_time=target_dining_time,
        requires_wheelchair=requires_wheelchair
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_dining_session(db: Session, session_id):
    return db.query(DiningSession).filter(DiningSession.session_id == session_id).first()

def update_dining_session(db: Session, session_id, **kwargs):
    session_obj = get_dining_session(db, session_id)
    if session_obj:
        for key, value in kwargs.items():
            setattr(session_obj, key, value)
        db.commit()
        db.refresh(session_obj)
    return session_obj

def delete_dining_session(db: Session, session_id):
    session_obj = get_dining_session(db, session_id)
    if session_obj:
        db.delete(session_obj)
        db.commit()
        return True
    return False

# --- SESSION MEMBER CRUD ---

def add_session_member(db: Session, session_id, user_id, starting_location: str, max_travel_radius: int = None):
    # starting_location should be a WKT string 'POINT(long lat)'
    member = SessionMember(
        session_id=session_id,
        user_id=user_id,
        starting_location=starting_location,
        max_travel_radius=max_travel_radius
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def get_session_member(db: Session, session_id, user_id):
    return db.query(SessionMember).filter(SessionMember.session_id == session_id, SessionMember.user_id == user_id).first()

def get_session_members(db: Session, session_id):
    return db.query(SessionMember).filter(SessionMember.session_id == session_id).all()

def update_session_member(db: Session, session_id, user_id, **kwargs):
    member = get_session_member(db, session_id, user_id)
    if member:
        for key, value in kwargs.items():
            setattr(member, key, value)
        db.commit()
        db.refresh(member)
    return member

def remove_session_member(db: Session, session_id, user_id):
    member = get_session_member(db, session_id, user_id)
    if member:
        db.delete(member)
        db.commit()
        return True
    return False

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
        query = query.filter(session.max_price_level <= Restaurant.max_price)

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

