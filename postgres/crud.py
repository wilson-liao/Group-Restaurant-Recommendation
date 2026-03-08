from sqlalchemy.orm import Session
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

def create_restaurant(db: Session, place_id: str, location: str, rating: float = None, price_level: int = None, wheelchair_accessible: bool = None, opening_hours: dict = None):
    # Location should be passed as a WKT string, e.g., 'POINT(-71.060316 48.432044)'
    restaurant = Restaurant(
        place_id=place_id,
        location=location,
        rating=rating,
        price_level=price_level,
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
