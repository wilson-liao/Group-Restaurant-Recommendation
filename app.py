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
from utils.dietary_classifier import DIETARY_KEYWORDS
from utils.cuisine_classifier import CUISINE_KEYWORDS

import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geoalchemy2.shape import to_shape

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
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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
CUISINE_OPTIONS = list(CUISINE_KEYWORDS.keys())
RESTRICTION_OPTIONS = list(DIETARY_KEYWORDS.keys())

# --- STATE MANAGEMENT ---
if 'selected_users' not in st.session_state:
    st.session_state.selected_users = []
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'selected_restaurant_id' not in st.session_state:
    st.session_state.selected_restaurant_id = None
if 'config_expanded' not in st.session_state:
    st.session_state.config_expanded = True

def refresh_users():
    """Fetches all users from DB to populate selector"""
    return {str(u.user_id): u.name for u in pg_crud.get_users(db, limit=1000)}

all_users_dict = refresh_users()

def format_opening_hours(periods):
    """Convert Google Places JSON period data into a readable string list."""
    if not periods:
        return ["Open Hours Not Available"]
        
    days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    # Check if 24/7 (Only 1 period, day 0, open time 0000, no close)
    if len(periods) == 1 and periods[0].get("open", {}).get("day") == 0 and not periods[0].get("close"):
        return ["Open 24 Hours, 7 Days a week"]

    def to_12h(h, m):
        if h == 0:
            return f"12:{m:02d} AM"
        elif h < 12:
            return f"{h}:{m:02d} AM"
        elif h == 12:
            return f"12:{m:02d} PM"
        else:
            return f"{h-12}:{m:02d} PM"

    day_blocks = {day: [] for day in range(7)}

    for period in periods:
        open_data = period.get("open", {})
        close_data = period.get("close", {})
        
        day_idx = open_data.get("day")
        if day_idx is None:
            continue
            
        open_time_str = to_12h(open_data.get('hour', 0), open_data.get('minute', 0))
        if close_data:
            close_time_str = to_12h(close_data.get('hour', 0), close_data.get('minute', 0))
            day_blocks[day_idx].append(f"{open_time_str} - {close_time_str}")
        else:
            day_blocks[day_idx].append(f"Opens at {open_time_str}")
             
    formatted_hours = []
    
    # Render starting from Sunday -> Saturday to maintain consistent ordering
    for day_idx in range(7):
        if day_blocks[day_idx]:
            day_name = days_of_week[day_idx]
            times_str = ", ".join(day_blocks[day_idx])
            formatted_hours.append(f"{day_name}: {times_str}")
            
    return formatted_hours

@st.dialog("⚠️ Delete All Sessions")
def delete_all_sessions_dialog():
    st.warning("This will permanently delete all dining sessions from the database.")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    
    with st.form("delete_sessions_form"):
        pwd_input = st.text_input("Admin Password", type="password")
        if st.form_submit_button("Delete All"):
            if pwd_input == admin_password:
                try:
                    # 1. Delete from Postgres
                    pg_crud.delete_all_sessions(db)
                    
                    # 2. Delete from Neo4j
                    neo4j_conn.delete_all_sessions()
                    
                    st.session_state.current_session_id = None
                    st.session_state.selected_restaurant_id = None
                    st.session_state.config_expanded = True
                    st.success("All sessions deleted successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting sessions: {e}")
            else:
                st.error("Invalid password")

@st.dialog("👤 Create New User")
def create_user_dialog():
    st.write("Add someone new to the database.")
    
    with st.form("new_user_form", clear_on_submit=True):
        new_name = st.text_input("Name", placeholder="e.g. Alex Johnson")
        new_restrictions = st.multiselect("Permanent Dietary Restrictions", RESTRICTION_OPTIONS)
        
        if st.form_submit_button("Add User to Database", use_container_width=True):
            if new_name.strip():
                try:
                    # 1. Postgres User Creation
                    pg_user = pg_crud.create_user(db, name=new_name)
                    # 2. Add Data to Neo4j
                    neo4j_conn.add_user_to_neo4j(str(pg_user.user_id), pg_user.name, new_restrictions)
                    
                    # Clear any active session results to start fresh
                    st.session_state.current_session_id = None
                    st.session_state.selected_restaurant_id = None
                    st.session_state.config_expanded = True
                    
                    st.success(f"Added {new_name}!")
                    st.rerun() # Refresh the user dict instantly
                except Exception as e:
                    st.error(f"Error creating user: {e}")
            else:
                st.warning("Name is required.")

# --- UI COMPONENTS ---
header_col1, header_col2, header_col3 = st.columns([2.5, 1, 1])
with header_col1:
    st.title("🍽️ Start a Dining Session")
    st.markdown("<p style='color: #718096; font-size: 1.1rem; margin-bottom: 2rem;'>Configure your group and instantly synchronize everyone's preferences.</p>", unsafe_allow_html=True)
with header_col2:
    st.write("") # vertical spacing padding
    if st.button("➕ Create New User", use_container_width=True):
        create_user_dialog()
with header_col3:
    st.write("")
    if st.button("🗑️ Delete All Sessions", use_container_width=True, type="secondary"):
        delete_all_sessions_dialog()

# --- MAIN BODY: SESSION CONFIGURATION ---
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

# Main wrapper for session dynamic inputs
with st.expander("2. Configure Session & Individual Preferences", expanded=st.session_state.config_expanded):
    st.subheader("Session Details")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        target_date = st.date_input("Target Dining Date", value=datetime.today())
        target_time = st.time_input("Target Dining Time", value=time(19, 0))
        wheelchair_needed = st.checkbox("Requires Wheelchair Accessible Venue")
    with col_s2:
        max_group_price = st.number_input("Max Price ($ USD) for Group (Optional)", min_value=1, value=None, step=5, placeholder="Unlimited")

    st.subheader("3. Individual Preferences")
    user_data = {} # Store dynamically collected data here
    
    # Render dynamic block for each selected user
    for uid in selected_ids:
        uname = all_users_dict[uid]
        st.markdown(f"<div class='user-card'><h4>{uname}</h4>", unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.write("**Location Selection**")
            
            default_lat, default_lng = 32.8801, -117.2340
            
            # Ensure the user's lat/lng is instantiated in session state
            if f"lat_final_{uid}" not in st.session_state:
                st.session_state[f"lat_final_{uid}"] = default_lat
                st.session_state[f"lng_final_{uid}"] = default_lng
            
            # Read current working coords
            lat = st.session_state[f"lat_final_{uid}"]
            lng = st.session_state[f"lng_final_{uid}"]
            
            addr_input = st.text_input("Enter Address (Optional)", key=f"addr_input_{uid}")
            
            # Check if address input changed
            if f"last_addr_input_{uid}" not in st.session_state:
                st.session_state[f"last_addr_input_{uid}"] = ""
                
            if addr_input and addr_input != st.session_state[f"last_addr_input_{uid}"]:
                try:
                    geolocator = Nominatim(user_agent="forksync")
                    location = geolocator.geocode(addr_input)
                    if location:
                        st.session_state[f"lat_final_{uid}"] = float(location.latitude)
                        st.session_state[f"lng_final_{uid}"] = float(location.longitude)
                        st.session_state[f"last_addr_input_{uid}"] = addr_input
                        st.success(f"Found: {location.address}")
                        st.rerun()
                    else:
                        st.error("Address not found. Please try another or click on the map.")
                        st.session_state[f"last_addr_input_{uid}"] = addr_input
                except:
                    pass
            elif not addr_input:
                st.session_state[f"last_addr_input_{uid}"] = ""
            
            m = folium.Map(location=[lat, lng], zoom_start=13)
            folium.Marker([lat, lng], popup="Starting Point", tooltip="Your Location").add_to(m)
            
            # Use st_folium to capture click events
            st_data = st_folium(m, width=350, height=300, key=f"map_{uid}")
            
            if st_data and st_data.get("last_clicked"):
                clicked_lat = float(st_data["last_clicked"]["lat"])
                clicked_lng = float(st_data["last_clicked"]["lng"])
                
                processed_lat_key = f"processed_click_lat_{uid}"
                processed_lng_key = f"processed_click_lng_{uid}"
                
                last_processed_lat = st.session_state.get(processed_lat_key, None)
                last_processed_lng = st.session_state.get(processed_lng_key, None)
                
                if clicked_lat != last_processed_lat or clicked_lng != last_processed_lng:
                    # NEW click detected!
                    st.session_state[processed_lat_key] = clicked_lat
                    st.session_state[processed_lng_key] = clicked_lng
                    
                    st.session_state[f"lat_final_{uid}"] = clicked_lat
                    st.session_state[f"lng_final_{uid}"] = clicked_lng
                    st.rerun()

            # Provide manual override tracking
            final_lat = st.number_input(f"Selected Latitude", value=lat, format="%.6f", key=f"lat_final_{uid}")
            final_lng = st.number_input(f"Selected Longitude", value=lng, format="%.6f", key=f"lng_final_{uid}")

        with c2:
            radius = st.number_input(f"Max Travel Radius", min_value=1.0, value=15.0, step=1.0, key=f"rad_{uid}")
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
            "lat": final_lat,
            "lng": final_lng,
            "radius": radius,
            "unit": unit,
            "cuisines": {k: v for k, v in c_scores.items() if v > 0} # only save non-zero scores
        }
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    submit_session = st.button("🚀 Launch Dining Session", type="primary", use_container_width=True)
    
    # --- PROCESSING LOGIC ---
    if submit_session:
        try:
            # Determine creator (arbitrarily pick the first selected user, or assume there's a logged in user logic. Using first for now.)
            creator_id = uuid.UUID(selected_ids[0])
            
            # Combine selected date with target_time to create a timestamp
            dt_target = datetime.combine(target_date, target_time)
            
            # 1. Postgres Create Session
            pg_session = pg_crud.create_dining_session(
                db, 
                creator_id=creator_id,
                max_price_level=max_group_price,  # NOTE: the schema field is actually max_price_level so we are still passing it effectively as max_price
                target_dining_time=dt_target,
                requires_wheelchair=wheelchair_needed
            )
            session_uuid = str(pg_session.session_id)
            
            # 2. Add Session Data to Neo4j
            neo4j_conn.add_session_data_to_neo4j(session_uuid, user_data)

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

            # Persist the session ID in the Streamlit state
            st.session_state.current_session_id = session_uuid
            st.session_state.config_expanded = False # Collapse the inputs

            st.success(f"🎉 Session Successfully Launched! ID: {session_uuid}")
            st.balloons()
            
        except Exception as e:
            st.error(f"Failed to create session: {e}")

# --- PERSISTENT RESULTS DISPLAY ---
if st.session_state.current_session_id:
    try:
        session_uuid = st.session_state.current_session_id
        
        from utils.filtering import filter_restaurants_by_neo4j, get_filtered_restaurants_for_session
        # Fetch filtered restaurants from Postgres
        pg_filtered = get_filtered_restaurants_for_session(db, session_uuid)
        
        # Filter and score with Neo4j
        # Filter and score with Neo4j, limiting to top 50
        scored_restaurants = filter_restaurants_by_neo4j(neo4j_conn, session_uuid, pg_filtered)
        top_scored = scored_restaurants[:50]
        filtered_restaurants = [item["restaurant"] for item in top_scored]
        
        # Look up restaurant names, cuisines, and dietary restrictions in Neo4j
        place_ids = [r.place_id for r in filtered_restaurants]
        query = """
        MATCH (r:Restaurant) WHERE r.place_id IN $place_ids 
        OPTIONAL MATCH (r)-[:SERVES]->(c:Cuisine)
        OPTIONAL MATCH (r)-[:ACCOMMODATES]->(d:DietaryRestriction)
        RETURN r.place_id AS place_id, r.name AS name, collect(DISTINCT c.name) AS cuisines, collect(DISTINCT d.name) AS restrictions
        """
        neo_records = neo4j_conn._execute_read(query, place_ids=place_ids)
        info_map = {rec["place_id"]: {"name": rec["name"], "cuisines": rec["cuisines"], "restrictions": rec["restrictions"]} for rec in neo_records}
        
        # Fetch session members to get their start locations and radiuses
        session_members = pg_crud.get_session_members(db, session_uuid)
        member_locations = []
        for m in session_members:
            geom = to_shape(m.starting_location)
            uname = all_users_dict[str(m.user_id)]
            member_locations.append({
                "name": uname, 
                "lat": geom.y, 
                "lng": geom.x, 
                "radius": m.max_travel_radius
            })

        st.markdown("---")
        
        # Display Cuisine Scores
        cuisine_scores_query = """
        MATCH (u:User)-[r:DESIRES_CUISINE {session_id: $session_id}]->(c:Cuisine)
        WHERE r.score > 0
        WITH c.name AS cuisine, sum(r.score) AS score, collect(u.name + ': ' + toString(r.score)) AS breakdown
        RETURN cuisine, score, breakdown
        ORDER BY score DESC
        """
        cuisine_scores_records = neo4j_conn._execute_read(cuisine_scores_query, session_id=session_uuid)
        
        if cuisine_scores_records:
            st.subheader("📊 Group Cuisine Preferences")
            import pandas as pd
            import altair as alt

            df_scores = pd.DataFrame(cuisine_scores_records)
            df_scores["score"] = pd.to_numeric(df_scores["score"])
            # Filter out scores of 0 so they don't visually clutter the pack
            df_scores = df_scores[df_scores["score"] > 0]
            
            if not df_scores.empty:
                max_score = df_scores["score"].max()
                
                import streamlit.components.v1 as components
                import json
                
                colors = ["#FF4B4B", "#10b981", "#8b5cf6", "#f59e0b", "#3b82f6", "#ec4899", "#14b8a6", "#f43f5e", "#84cc16", "#06b6d4"]
                
                # Prepare JSON data for D3
                d3_data = []
                for i, row in df_scores.iterrows():
                    d3_data.append({
                        "id": row['cuisine'], 
                        "value": row['score'], 
                        "color": colors[i % len(colors)],
                        "breakdown": row['breakdown']
                    })
                
                # Dynamically calculate container size based on number of cuisines
                num_cuisines = len(df_scores)
                container_size = min(900, max(500, 300 + (num_cuisines * 40)))
                
                html_code = f"""
                <!DOCTYPE html>
                <html>
                <head>
                  <script src="https://d3js.org/d3.v7.min.js"></script>
                  <style>
                    body {{ margin: 0; overflow: hidden; background-color: transparent; font-family: sans-serif; height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; box-sizing: border-box; }}
                    #container {{ width: {container_size}px; height: {container_size}px; border-radius: 50%; background-color: #f8fafc; border: 2px dashed #cbd5e1; position: relative; overflow: hidden; box-shadow: inset 0 4px 6px rgba(0,0,0,0.05); flex-shrink: 0; }}
                    svg {{ width: 100%; height: 100%; }}
                    .tooltip {{
                      position: absolute;
                      text-align: center;
                      padding: 12px 16px;
                      font: 14px sans-serif;
                      font-weight: bold;
                      background: rgba(15, 23, 42, 0.95);
                      color: white;
                      border-radius: 12px;
                      border: 1px solid rgba(255, 255, 255, 0.1);
                      backdrop-filter: blur(4px);
                      pointer-events: none;
                      opacity: 0;
                      transition: opacity 0.2s;
                      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
                      z-index: 10;
                    }}
                    .node circle {{ cursor: pointer; transition: stroke-width 0.2s, stroke 0.2s; }}
                    .node text {{ pointer-events: none; user-select: none; }}
                  </style>
                </head>
                <body>
                <div id="container">
                  <svg></svg>
                </div>
                <div class="tooltip" id="tooltip"></div>
                
                <script>
                  const data = {json.dumps(d3_data)};
                
                  const width = {container_size};
                  const height = {container_size};
                  const centerX = width / 2;
                  const centerY = height / 2;
                  const radiusBoundary = width / 2 - 5;
                
                  const svg = d3.select("svg").attr("viewBox", [0, 0, width, height]);
                
                  const maxVal = d3.max(data, d => d.value) || 1;
                  
                  // Calculate dynamic optimal radius packing based on number of cuisines
                  const numNodes = data.length || 1;
                  const safeArea = Math.PI * Math.pow(radiusBoundary, 2) * 0.45; // Fill ~45% of the circle area
                  const idealMaxNodeArea = safeArea / numNodes; 
                  const idealMaxRadius = Math.sqrt(idealMaxNodeArea / Math.PI);
                  
                  const minR = Math.max(15, Math.min(35, idealMaxRadius * 0.4));
                  const maxR = Math.max(30, Math.min(100, idealMaxRadius));
                  
                  // Bubbly sizes (dynamic limits with exponential scaling to exaggerate differences)
                  const sizeScale = d3.scalePow().exponent(1.5).domain([0, maxVal]).range([minR, maxR]);
                
                  const simulation = d3.forceSimulation(data)
                    .force("charge", d3.forceManyBody().strength(15)) // slight push apart
                    .force("collide", d3.forceCollide().radius(d => sizeScale(d.value) + 2).iterations(4))
                    .force("center", d3.forceCenter(centerX, centerY).strength(0.05))
                    .force("x", d3.forceX(centerX).strength(0.04))
                    .force("y", d3.forceY(centerY).strength(0.04));
                
                  const tooltip = d3.select("#tooltip");
                
                  const node = svg.append("g")
                    .selectAll("g")
                    .data(data)
                    .join("g")
                    .attr("class", "node")
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended))
                    .on("mouseover", function(event, d) {{
                        d3.select(this).select("circle")
                           .transition().duration(200)
                           .attr("r", sizeScale(d.value) * 1.1)
                           .attr("stroke", "#334155")
                           .attr("stroke-width", 4);
                           
                        let breakdownHtml = d.breakdown.map(b => "<div style='font-size:13px; font-weight:normal; color:#cbd5e1; text-align:left; display:flex; justify-content:space-between; margin-top:2px;'><span>" + b.split(":")[0] + "</span><span style='color:#94a3b8; font-weight:bold;'>" + b.split(":")[1] + "</span></div>").join("");
                           
                        tooltip.transition().duration(200).style("opacity", 1);
                        tooltip.html("<div style='font-size: 16px; font-weight: 800; margin-bottom: 2px;'>" + d.id + "</div><div style='font-size: 14px; font-weight: 500; color: #94a3b8;'>Score: <span style='font-size: 18px; font-weight: 900; color: #38bdf8;'>" + d.value + "</span></div><hr style='border-color: rgba(255,255,255,0.1); margin: 8px 0;'/>" + breakdownHtml)
                           .style("left", (event.pageX + 25) + "px")
                           .style("top", (event.pageY - 45) + "px");
                    }})
                    .on("mousemove", function(event) {{
                        tooltip.style("left", (event.pageX + 25) + "px")
                               .style("top", (event.pageY - 45) + "px");
                    }})
                    .on("mouseout", function(event, d) {{
                        d3.select(this).select("circle")
                           .transition().duration(200)
                           .attr("r", sizeScale(d.value))
                           .attr("stroke", null);
                           
                        tooltip.transition().duration(300).style("opacity", 0);
                    }});
                
                  // Draw circles
                  node.append("circle")
                    .attr("r", d => sizeScale(d.value))
                    .attr("fill", d => d.color)
                    .attr("filter", "drop-shadow(0px 4px 4px rgba(0,0,0,0.15))");
                
                  // Draw Cuisine Name
                  node.append("text")
                    .attr("text-anchor", "middle")
                    .attr("dy", "-0.2em")
                    .style("fill", "white")
                    .style("font-size", d => Math.max(12, sizeScale(d.value)/3.5) + "px")
                    .style("font-weight", "bold")
                    .style("text-shadow", "0px 1px 3px rgba(0,0,0,0.5)")
                    .text(d => d.id);
                
                  // Draw Score Number
                  node.append("text")
                    .attr("text-anchor", "middle")
                    .attr("dy", "1em")
                    .style("fill", "white")
                    .style("font-size", d => Math.max(14, sizeScale(d.value)/2.5) + "px")
                    .style("font-weight", "900")
                    .style("text-shadow", "0px 1px 3px rgba(0,0,0,0.5)")
                    .text(d => d.value);
                
                  // Apply physics constraints so they bounce on the circular walls
                  simulation.on("tick", () => {{
                    node.attr("transform", d => {{
                        const r = sizeScale(d.value);
                        // Current distance from center
                        const dx = d.x - centerX;
                        const dy = d.y - centerY;
                        const dist = Math.sqrt(dx*dx + dy*dy);
                        
                        // If bubble pushes outside the transparent circular dashed border
                        if (dist > radiusBoundary - r) {{
                            const ratio = (radiusBoundary - r) / dist;
                            d.x = centerX + dx * ratio;
                            d.y = centerY + dy * ratio;
                        }}
                        return `translate(${{d.x}},${{d.y}})`;
                    }});
                  }});
                
                  // Dragging physics
                  function dragstarted(event) {{
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    event.subject.fx = event.subject.x;
                    event.subject.fy = event.subject.y;
                  }}
                  function dragged(event) {{
                    event.subject.fx = event.x;
                    event.subject.fy = event.y;
                  }}
                  function dragended(event) {{
                    if (!event.active) simulation.alphaTarget(0);
                    event.subject.fx = null;
                    event.subject.fy = null;
                  }}
                </script>
                </body>
                </html>
                """
                components.html(html_code, height=container_size + 40)
            else:
                st.info("No cuisine preferences were specified by the group.")

        st.subheader(f"Found {len(filtered_restaurants)} restaurants matching group criteria:")
        
        if filtered_restaurants:
            reg_col, map_col = st.columns([1, 2.5]) 
            
            with reg_col:
                # Wrap the restaurants in a scrollable container
                with st.container(height=600):
                    for i, item in enumerate(top_scored):
                        r = item["restaurant"]
                        r_score = item["score"]
                        r_info = info_map.get(r.place_id, {"name": "Unknown", "cuisines": [], "restrictions": []})
                        r_name = r_info["name"]
                        cuisines = r_info["cuisines"]
                        restrictions = r_info["restrictions"]
                        
                        with st.expander(f"🍽️ {r_name} (⭐️ {r.rating}) — Score: {r_score}"):
                            if r.min_price is not None and r.max_price is not None:
                                price_str = f"💵 ${r.min_price:,.2f} - ${r.max_price:,.2f}"
                            elif r.min_price is not None:
                                price_str = f"💵 From ${r.min_price:,.2f}"
                            elif r.max_price is not None:
                                price_str = f"💵 Up to ${r.max_price:,.2f}"
                            else:
                                price_str = "💵 Price Unknown"
                                
                            st.markdown(f"<div class='price-badge'>{price_str}</div>", unsafe_allow_html=True)
                            st.write(f"**Wheelchair Accessible:** {'Yes' if r.wheelchair_accessible else 'No'}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if r.types:
                                    # Show up to 3 types, neatly formatted
                                    formatted_types = [t.replace('_', ' ').title() for t in r.types[:3]]
                                    st.write(f"**Types:** {', '.join(formatted_types)}")
                                if cuisines:
                                    st.write(f"**Cuisine:** {', '.join(cuisines)}")
                            with col2:
                                if restrictions:
                                    st.write(f"**Dietary:** {', '.join(restrictions)}")
                            
                            
                            if r.google_maps_uri:
                                st.markdown(f"[📍 Open in Google Maps]({r.google_maps_uri})")
                            
                            if r.opening_hours and "periods" in r.opening_hours:
                                st.write("**Opening Hours:**")
                                hours_list = format_opening_hours(r.opening_hours["periods"])
                                for h in hours_list:
                                    st.write(f"- {h}")
                                    
                            if st.button(f"📍 View '{r_name}' on Map", key=f"btn_map_{r.place_id}"):
                                st.session_state.selected_restaurant_id = r.place_id
                                st.rerun()

            with map_col:
                # Determine Map Center
                # If a restaurant is selected, center on it. Otherwise, average user locations.
                map_lat, map_lng = 32.8801, -117.2340 # Default backup
                selected_r = None
                
                if st.session_state.selected_restaurant_id:
                    # Find the restaurant object
                    for r in filtered_restaurants:
                        if r.place_id == st.session_state.selected_restaurant_id:
                            selected_r = r
                            break
                
                if selected_r:
                    r_geom = to_shape(selected_r.location)
                    map_lat, map_lng = r_geom.y, r_geom.x
                elif member_locations:
                    map_lat = sum([loc['lat'] for loc in member_locations]) / len(member_locations)
                    map_lng = sum([loc['lng'] for loc in member_locations]) / len(member_locations)
                    
                # Initialize Unified Map
                m_unified = folium.Map(location=[map_lat, map_lng], zoom_start=12 if selected_r else 11)
                
                # Pin all users and draw their travel radiuses
                for loc in member_locations:
                    # User pin
                    folium.Marker(
                        [loc["lat"], loc["lng"]],
                        popup=f"User: {loc['name']}",
                        tooltip=loc["name"],
                        icon=folium.Icon(color="blue", icon="user")
                    ).add_to(m_unified)
                    
                    # User max travel radius circle
                    if loc.get("radius"):
                        folium.Circle(
                            location=[loc["lat"], loc["lng"]],
                            radius=loc["radius"],
                            color="blue",
                            weight=1,
                            fill=True,
                            fill_opacity=0.1
                        ).add_to(m_unified)
                    
                # Pin the selected restaurant (if any)
                if selected_r:
                    r_info = info_map.get(selected_r.place_id, {"name": "Unknown"})
                    r_name = r_info.get("name", "Selected Restaurant")
                    r_geom = to_shape(selected_r.location)
                    folium.Marker(
                        [r_geom.y, r_geom.x], 
                        popup=f"<b>{r_name}</b>", 
                        tooltip=r_name,
                        icon=folium.Icon(color="red", icon="star")
                    ).add_to(m_unified)

                st_folium(m_unified, width="100%", height=700, key=f"unified_map_{session_uuid}")
                
                if selected_r:
                    st.info(f"Currently viewing: **{info_map.get(selected_r.place_id, {}).get('name', 'Unknown')}**")
                else:
                    st.info("👈 Click **View on Map** in a restaurant's details to see its location.")
                    
        else:
            st.warning("No restaurants found that meet everyone's constraints!")
        
        # Option to start over
        if st.button("🔄 Configure New Session", use_container_width=True):
            st.session_state.current_session_id = None
            st.session_state.selected_restaurant_id = None
            st.session_state.config_expanded = True
            st.rerun()

    except Exception as e:
        st.error(f"Failed to fetch matching restaurants: {e}")
