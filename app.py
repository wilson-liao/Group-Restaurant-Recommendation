import streamlit as st
import uuid
import urllib.parse
import os
from datetime import datetime, time
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import CRUD and Models
from postgres.models import Base
import postgres.crud as pg_crud
from neo4j_utils.crud import Neo4jConnector

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ForkSync | Start a Session",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #f7f9fc; color: #1a202c; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #2d3748; font-weight: 700; }
    .user-card { background: #f8fafc; padding: 16px; border-radius: 8px; border-left: 4px solid #3182ce; margin-bottom: 16px; }
    hr { margin-top: 1rem; margin-bottom: 1rem; border: 0; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION LOGIC ---
@st.cache_resource
def get_db_connections():
    load_dotenv()
    try:
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
        Base.metadata.create_all(bind=engine)
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        return SessionLocal, neo4j_conn
    except Exception as e:
        st.error(f"Failed to connect to databases.\n\n{e}")
        return None, None

SessionLocal, neo4j_conn = get_db_connections()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if not SessionLocal or not neo4j_conn:
    st.stop()

db = next(get_db())

# --- CONSTANTS ---
CUISINE_OPTIONS = ["Italian", "Mexican", "Thai", "Japanese", "Chinese", "American", "Indian", "Mediterranean", "Korean", "French", "Vietnamese", "Greek", "Vegan/Healthy"]
RESTRICTION_OPTIONS = ["Vegan", "Vegetarian", "Gluten-Free", "Dairy-Free", "Nut Allergy", "Halal", "Kosher", "Pescatarian"]

# --- STATE MANAGEMENT ---
if 'selected_users' not in st.session_state:
    st.session_state.selected_users = []

def refresh_users():
    """Fetches all users from DB to populate selector"""
    return {str(u.user_id): u.name for u in pg_crud.get_users(db, limit=1000)}

all_users_dict = refresh_users()

# --- UI COMPONENTS ---
st.title("🍽️ Start a Dining Session")
st.markdown("<p style='color: #718096; font-size: 1.1rem; margin-bottom: 2rem;'>Configure your group and instantly synchronize everyone's preferences.</p>", unsafe_allow_html=True)

col_main, col_sidebar = st.columns([2, 1])

# --- SIDEBAR: CREATE NEW USER ---
with col_sidebar:
    st.subheader("👤 Create New User")
    st.write("Add someone new to the database.")
    
    with st.form("new_user_form", clear_on_submit=True):
        new_name = st.text_input("Name", placeholder="e.g. Alex Johnson")
        new_restrictions = st.multiselect("Permanent Dietary Restrictions", RESTRICTION_OPTIONS)
        
        if st.form_submit_button("Add User to Database", use_container_width=True):
            if new_name.strip():
                try:
                    # 1. Postgres User Creation
                    pg_user = pg_crud.create_user(db, name=new_name)
                    # 2. Neo4j User Node Creation
                    neo4j_conn.create_user(user_id=str(pg_user.user_id), name=pg_user.name)
                    
                    # 3. Add Restrictions to Neo4j
                    for res in new_restrictions:
                        neo4j_conn.create_dietary_restriction(name=res)
                        neo4j_conn.add_user_restriction(user_id=str(pg_user.user_id), restriction_name=res)
                    
                    st.success(f"Added {new_name}!")
                    st.rerun() # Refresh the user dict instantly
                except Exception as e:
                    st.error(f"Error creating user: {e}")
            else:
                st.warning("Name is required.")

# --- MAIN BODY: SESSION CONFIGURATION ---
with col_main:
    st.subheader("1. Select Your Group")
    
    # User Selector
    user_options = list(all_users_dict.keys())
    selected_ids = st.multiselect(
        "Search and select participating users:",
        options=user_options,
        default=st.session_state.selected_users,
        format_func=lambda x: f"{all_users_dict[x]} (ID: {x.split('-')[0]})"
    )
    st.session_state.selected_users = selected_ids
    
    if not selected_ids:
        st.info("👈 Select users from the dropdown or create a new user to begin configuring the session.")
        st.stop()
    
    # Form wrapper for all dynamic inputs
    with st.form("session_creation_form"):
        st.subheader("2. Session Details")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            target_time = st.time_input("Target Dining Time", value=time(19, 0))
            wheelchair_needed = st.checkbox("Requires Wheelchair Accessible Venue")
        with col_s2:
            max_group_price = st.number_input("Max Price ($ USD) for Group", min_value=1, value=50, step=5)

        st.subheader("3. Individual Preferences")
        user_data = {} # Store dynamically collected data here
        
        # Render dynamic block for each selected user
        for uid in selected_ids:
            uname = all_users_dict[uid]
            st.markdown(f"<div class='user-card'><h4>{uname}</h4>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                lat = st.number_input(f"Starting Latitude", value=32.8801, format="%.6f", key=f"lat_{uid}")
                lng = st.number_input(f"Starting Longitude", value=-117.2340, format="%.6f", key=f"lng_{uid}")
            with c2:
                radius = st.number_input(f"Max Travel Radius", min_value=1.0, value=5.0, step=1.0, key=f"rad_{uid}")
                unit = st.selectbox(f"Distance Unit", ["Miles", "Kilometers"], key=f"unit_{uid}")
            
            # Cuisines expander to save vertical space
            with st.expander(f"Rate Cuisines for {uname}"):
                c_scores = {}
                # Create a mini-grid for sliders
                sc1, sc2 = st.columns(2)
                for idx, cuisine in enumerate(CUISINE_OPTIONS):
                    col_target = sc1 if idx % 2 == 0 else sc2
                    c_scores[cuisine] = col_target.slider(cuisine, min_value=0, max_value=10, value=0, key=f"c_{cuisine}_{uid}")
            
            # Save to dictionary for processing on submit
            user_data[uid] = {
                "lat": lat,
                "lng": lng,
                "radius": radius,
                "unit": unit,
                "cuisines": {k: v for k, v in c_scores.items() if v > 0} # only save non-zero scores
            }
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        submit_session = st.form_submit_button("🚀 Launch Dining Session", type="primary", use_container_width=True)
        
        # --- PROCESSING LOGIC ---
        if submit_session:
            try:
                # Determine creator (arbitrarily pick the first selected user, or assume there's a logged in user logic. Using first for now.)
                creator_id = uuid.UUID(selected_ids[0])
                
                # Combine today's date with target_time to create a timestamp
                dt_target = datetime.combine(datetime.today(), target_time)
                
                # We need a central target_location. For this logic, we'll arbitrarily use the creator's location
                # Ideally the matching algo calculates the centroid later, but the schema requires target_location on creation.
                c_data = user_data[selected_ids[0]]
                t_loc_wkt = f"POINT({c_data['lng']} {c_data['lat']})"

                # 1. Postgres Create Session
                pg_session = pg_crud.create_dining_session(
                    db, 
                    creator_id=creator_id,
                    target_location=t_loc_wkt,
                    max_price_level=max_group_price,
                    target_dining_time=dt_target,
                    requires_wheelchair=wheelchair_needed
                )
                session_uuid = str(pg_session.session_id)
                
                # 2. Neo4j Create Session Node
                neo4j_conn.create_session(session_id=session_uuid)

                # 3. Process every user in the session
                for uid_str, data in user_data.items():
                    u_uuid = uuid.UUID(uid_str)
                    
                    # Convert Radius to meters for Postgres (1 mile = 1609.34 meters, 1 km = 1000 meters)
                    rad_meters = int(data['radius'] * 1609.34) if data['unit'] == "Miles" else int(data['radius'] * 1000)
                    start_wkt = f"POINT({data['lng']} {data['lat']})"
                    
                    # A. Postgres Add Session Member
                    pg_crud.add_session_member(
                        db,
                        session_id=pg_session.session_id,
                        user_id=u_uuid,
                        starting_location=start_wkt,
                        max_travel_radius=rad_meters
                    )
                    
                    # B. Neo4j Add Join Edge
                    neo4j_conn.user_join_session(user_id=uid_str, session_id=session_uuid)
                    
                    # C. Neo4j Cuisine Preferences
                    for cuisine_name, score in data['cuisines'].items():
                        neo4j_conn.create_cuisine(name=cuisine_name)
                        neo4j_conn.user_desires_cuisine(
                            user_id=uid_str, 
                            cuisine_name=cuisine_name, 
                            session_id=session_uuid, 
                            score=score
                        )
                        neo4j_conn.update_session_cuisine_score(
                            session_id=session_uuid,
                            cuisine_name=cuisine_name
                        )

                st.success(f"🎉 Session Successfully Launched! ID: {session_uuid}")
                st.balloons()
                
            except Exception as e:
                st.error(f"Failed to create session: {e}")
