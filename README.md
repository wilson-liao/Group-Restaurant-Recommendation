# 🍽️ ForkSync

**ForkSync** is a unified Restaurant Recommendation System designed to synchronize group dining preferences. Planning a group dinner often involves endless text chains trying to compromise on location, budget, dietary restrictions, and cuisine cravings. ForkSync solves this by gathering everyone's individual preferences and utilizing a dual-database architecture to compute the perfect restaurant match for the entire group.

## ✨ Features
- **Centralized Group Sessions:** Form a dining group (session) by selecting registered users.
- **Dynamic Preferences:** Each user configures their personal preferences for the specific outing (Starting Location, Travel Radius, Cuisine Rating 1-10).
- **Permanent User Traits:** Users can securely store permanent traits like dietary restrictions (Vegan, Gluten-Free, Halal, etc.) which automatically apply to any session they join.
- **Dual-Database Architecture:**
  - **PostgreSQL / PostGIS:** Handles relational, structured, and spatial data (Users, Sessions, geographic coordinates, and radius constraints).
  - **Neo4j:** Handles complex graph relationships (User -> Cuisine Preferences, Restaurant -> Dietary Restrictions).
- **Streamlit Dashboard:** A sleek, single-page interface to orchestrate the entire workflow effortlessly.

## 🚀 Tech Stack
- **Frontend / UI:** Streamlit (Python)
- **Backend Graph Engine:** Neo4j Database
- **Backend Relational Engine:** PostgreSQL with PostGIS
- **ORM / Drivers:** SQLAlchemy, GeoAlchemy2, Neo4j Python Driver
- **Deployment:** Docker & Docker Compose

## 🛠️ Setup & Installation

### Prerequisites
1. [Docker](https://docs.docker.com/get-docker/) & Docker Compose installed.
2. [Python 3.9+](https://www.python.org/downloads/) installed.

### 1. Clone the Repository
```bash
git clone https://github.com/wilson-liao/Group-Restaurant-Recommendation.git
cd Group-Restaurant-Recommendation
```

### 2. Configure Environment Variables
Copy the example environment file and update it if necessary:
```bash
cp .env.example .env
```
*(By default, the provided `.env.example` configurations match the Docker Compose setup).*

### 3. Spin Up the Databases
ForkSync uses Docker to run both PostgreSQL and Neo4j locally.
```bash
docker-compose up -d
```
*Note: Make sure port `5433` (Postgres) and `7687`/`7474` (Neo4j) are available on your host machine.*

### 4. Install Python Dependencies
Create a virtual environment (recommended) and install the required packages:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Launch the Application
Start the Streamlit UI using the main driver script:
```bash
python main.py
```
Or run Streamlit directly:
```bash
streamlit run app.py
```
The application will open in your default web browser at `http://localhost:8501`.

## 📂 Project Structure
- `app.py`: The main Streamlit frontend application.
- `main.py`: CLI driver script to launch the application.
- `docker-compose.yml`: Docker orchestration for Postgres and Neo4j.
- `requirements.txt`: Python package dependencies.
- `postgres/`: SQLAlchemy models, PostGIS schemas, and CRUD operations.
- `neo4j_utils/`: Cypher queries and graph database CRUD wrappers.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
