-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE restaurants (
    place_id VARCHAR(255) PRIMARY KEY,
    location GEOMETRY(Point, 4326),
    rating FLOAT,
    price_level INT,
    wheelchair_accessible BOOLEAN,
    opening_hours JSONB
);

CREATE TABLE dining_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_id UUID REFERENCES users(user_id) ON DELETE CASCADE,

    max_price_level INT,
    target_dining_time TIMESTAMP,
    requires_wheelchair BOOLEAN
);

CREATE TABLE session_members (
    session_id UUID REFERENCES dining_sessions(session_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    starting_location GEOMETRY(Point, 4326),
    max_travel_radius INT,
    PRIMARY KEY (session_id, user_id)
);
