import uuid
import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship

# Import GeoAlchemy2 for the Geometry type (PostGIS)
from geoalchemy2 import Geometry

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class Restaurant(Base):
    __tablename__ = 'restaurants'
    
    place_id = Column(String(255), primary_key=True)
    location = Column(Geometry('POINT', srid=4326))
    rating = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    wheelchair_accessible = Column(Boolean)
    opening_hours = Column(JSONB)
    google_maps_uri = Column(String(500))
    types = Column(ARRAY(String))
    display_name = Column(String(255))
    primary_type = Column(String(255))

class DiningSession(Base):
    __tablename__ = 'dining_sessions'
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'))
    max_price_level = Column(Integer)
    target_dining_time = Column(TIMESTAMP)
    requires_wheelchair = Column(Boolean)
    
    # Relationship to the creator (User)
    creator = relationship("User")

class SessionMember(Base):
    __tablename__ = 'session_members'
    
    session_id = Column(UUID(as_uuid=True), ForeignKey('dining_sessions.session_id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    starting_location = Column(Geometry('POINT', srid=4326))
    max_travel_radius = Column(Integer)
    
    # Relationships
    session = relationship("DiningSession")
    user = relationship("User")
