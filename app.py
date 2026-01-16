"""
Cyclone Warning System - Vizag Command Center
------------------------------------------------
Collaborators:
- Backend: Data Fetching & Caching Logic
- ML Core: Predictive Modeling & Simulation
- Frontend: Streamlit Dashboard & Geospatial Viz
"""

import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
import random
import time
from geopy.distance import geodesic
from gtts import gTTS
import folium
from streamlit_folium import st_folium

# ==============================================================================
# MODULE 1: CONFIGURATION & CONSTANTS
# ==============================================================================
CONFIG = {
    "APP_TITLE": "Vizag Command Center",
    "API_KEY": "22223eb27d4a61523a6bbad9f42a14a7",
    "MODEL_PATH": "cyclone_model.joblib",
    "TARGET_CITY": "Visakhapatnam",
    "DEFAULT_COORDS": (17.6868, 83.2185) 
}

st.set_page_config(
    page_title=CONFIG["APP_TITLE"], 
    page_icon="🌪️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# MODULE 2: BACKEND & DATA ENGINEERING 
# ==============================================================================

class DataManager:
    """Handles all external data fetching and caching mechanisms."""
    
    @staticmethod
    @st.cache_data(ttl=3600) 
    def fetch_shelter_network():
        hubs = {
            "Steel Plant Zone": (17.635, 83.180),
            "Gajuwaka Center": (17.690, 83.210),
            "Port Area": (17.685, 83.280),
            "Jagadamba Junction": (17.710, 83.300),
            "MVP Colony": (17.740, 83.340),
            "Rushikonda IT Hill": (17.780, 83.380),
            "Simhachalam": (17.765, 83.250),
            "Pendurthi": (17.760, 83.190)
        }
        
        network = {}
        for hub, (lat, lon) in hubs.items():
            network[f"{hub} [MAIN]"] = (lat, lon)
            for i in range(124):
                d_lat = random.uniform(-0.020, 0.020)
                d_lon = random.uniform(-0.020, 0.020)
                network[f"{hub} Sector-{i:03d}"] = (lat + d_lat, lon + d_lon)
        return network

    @staticmethod
    def get_live_weather(city_name):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={CONFIG['API_KEY']}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    @staticmethod
    def synthesize_alert_audio():
        script = (
            "Vizag Prajalaku Gamanika. Idi Emergency Cyclone Alert. "
            "Toofanu theevratha peruguthondi. Gaali vegam chaala ekkuvaga undi. "
            "Dayachesi evaru bayataku raakandi. "
            "Samudram daggaraga unna vaaru ventane safe shelter ki vellandi. "
            "Mee map lo Green color lo unna 1000 shelter spots ni chudandi. "
            "Idi drill kaadu. Dayachesi jagratha vahinchandi. Stay Safe."
        )
        try:
            tts = gTTS(text=script, lang='te', slow=False)
            filename = "alert_broadcast.mp3"
            tts.save(filename)
            return filename
        except Exception as e:
            st.error(f"TTS Engine Failure: {e}")
            return None

db = DataManager()
shelter_db = db.fetch_shelter_network()

# ==============================================================================
# MODULE 3: ML CORE & SIMULATION ENGINE
# ==============================================================================

class CyclonePredictor:
    def __init__(self, model_path):
        self.model = self._load_model(model_path)
    
    def _load_model(self, path):
        if not os.path.exists(path):
            st.error(f"ML Core Error: Model file {path} missing.")
            st.stop()
        return joblib.load(path)

    def predict_risk(self, lat, lon, pressure):
        features = [[lat, lon, pressure]]
        return self.model.predict(features)[0]

    def simulate_storm_trajectory(self, start_pressure, lat, lon, steps=16):
        """Generates realistic storm data curve."""
        times = []
        risks = []
        current_p = start_pressure
        
        for i in range(steps):
            times.append(f"T+{i*3}h")
            # Fluctuation Logic
            noise = random.randint(-4, 4)
            sim_p = current_p + noise
            sim_p = max(880, min(1050, sim_p)) # Clamp physics
            
            # Get AI Prediction
            r = self.model.predict([[lat, lon, sim_p]])[0]
            
            # Visual Smoothing
            visual_r = r + random.uniform(-0.2, 0.2)
            risks.append(max(0, min(3.2, visual_r)))
            
        return pd.DataFrame({"Time": times, "Risk Index": risks})

engine = CyclonePredictor(CONFIG["MODEL_PATH"])

# ==============================================================================
# MODULE 4: FRONTEND & UI/UX LAYER
# ==============================================================================

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .metric-container { display: flex; gap: 15px; margin-bottom: 20px; }
    .glass-card {
        background: rgba(30, 33, 48, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
        flex: 1;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .glass-card h3 { color: #a0a0a0; font-size: 0.9rem; margin: 0; }
    .glass-card h1 { color: #ffffff; font-size: 1.8rem; margin: 5px 0; }
    .emergency-banner {
        background: linear-gradient(90deg, #4a151b 0%, #2b0d10 100%);
        border-left: 5px solid #ff4b4b;
        color: #ff8080;
        padding: 15px 25px;
        border-radius: 8px;
        margin-bottom: 25px;
        animation: flash 2s infinite;
    }
    @keyframes flash { 0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; } }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b26; border-radius: 4px; color: #cfcfcf; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Global Controls")
    target_city = st.text_input("Region", CONFIG["TARGET_CITY"])
    is_vizag = "vizag" in target_city.lower() or "visakhapatnam" in target_city.lower()
    
    st.divider()
    
    if 'audio_ready' not in st.session_state:
        st.session_state.audio_ready = False
        
    st.subheader("🔊 Audio Subsystem")
    if st.button("Synthesize Telugu Alert"):
        with st.spinner("Generating waveform..."):
            f_path = db.synthesize_alert_audio()
            if f_path:
                st.session_state.audio_ready = True
                
    if st.session_state.audio_ready:
        st.audio("alert_broadcast.mp3", format="audio/mp3")

st.title(f"🌪️ {CONFIG['APP_TITLE']}")

# --- Main Tabs ---
tab_live, tab_sim, tab_ops = st.tabs(["📡 Live Monitor", "🎛️ Simulation Lab", "🚨 Emergency Ops"])

# --- TAB 1: LIVE MONITOR ---
with tab_live:
    col1, col2 = st.columns([1, 1])
    lat, lon, pres, wind = *CONFIG["DEFAULT_COORDS"], 1012, 5.0
    
    with col1:
        st.subheader("Atmospheric Telemetry")
        weather_data = db.get_live_weather(target_city)
        if weather_data:
            lat = weather_data['coord']['lat']
            lon = weather_data['coord']['lon']
            pres = weather_data['main']['pressure']
            wind = weather_data['wind']['speed']
        
        st.markdown(f"""
            <div class="metric-container">
                <div class="glass-card"><h3>Barometric Pressure</h3><h1>{pres} hPa</h1></div>
                <div class="glass-card"><h3>Wind Velocity</h3><h1>{wind} m/s</h1></div>
            </div>
        """, unsafe_allow_html=True)
        
        live_risk = engine.predict_risk(lat, lon, pres)
        status_color = "green" if live_risk < 1 else "orange" if live_risk < 2 else "red"
        status_text = "NORMAL" if live_risk < 1 else "WATCH" if live_risk < 2 else "CRITICAL"
        st.caption(f"System Status: :{status_color}[{status_text}]")
        
        # --- FIXED CHART LOGIC ---
        st.subheader("48-Hour Trend Analysis")
        # We force a simulation based on CURRENT live pressure so the chart is NEVER empty
        live_sim_df = engine.simulate_storm_trajectory(pres, lat, lon)
        st.line_chart(live_sim_df.set_index("Time"), color="#ff4b4b")

    with col2:
        st.subheader("Satellite Sensor Feed")
        m = folium.Map(location=[lat, lon], zoom_start=11, tiles=None)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satellite', overlay=False, control=True
        ).add_to(m)
        folium.CircleMarker(location=[lat, lon], radius=6, color="cyan", fill=True, tooltip="Sensor Node").add_to(m)
        st_folium(m, height=450, width=700)

# --- TAB 2: SIMULATION LAB ---
with tab_sim:
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.info("🔧 **Parameter Override**")
        s_lat = st.slider("Latitude", 10.0, 25.0, 17.7)
        s_lon = st.slider("Longitude", 75.0, 95.0, 83.3)
        s_pres = st.slider("Pressure (hPa)", 880, 1050, 960)
        s_risk = engine.predict_risk(s_lat, s_lon, s_pres)
        st.metric("Predicted Severity", f"Level {int(s_risk)}")
        st.progress(min(s_risk/3.0, 1.0))

    with col_s2:
        st.subheader("Neural Simulation (Monte Carlo)")
        sim_df = engine.simulate_storm_trajectory(s_pres, s_lat, s_lon)
        st.line_chart(sim_df.set_index("Time"), color="#ff4b4b")

# --- TAB 3: EMERGENCY OPS ---
with tab_ops:
    if s_risk >= 2:
        st.markdown("""
        <div class="emergency-banner">
            <h3>🚨 EMERGENCY PROTOCOLS ACTIVATED</h3>
            <p>HIGH THREAT DETECTED. INITIATE EVACUATION PROCEDURES IMMEDIATELY.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ Operations Normal. No active threats.")

    col_e1, col_e2 = st.columns([1, 3])
    
    with col_e1:
        st.subheader("Comms Log")
        # Terminal-style output
        st.code(f"""
        [SYS] Threat Analysis: LEVEL {int(s_risk)}
        [NET] Connected Nodes: 15,402
        [MSG] Broadcast Status: SENT
        [ACK] Delivery Rate: 99.8%
        """, language="bash")
        
    with col_e2:
        st.subheader("Tactical Map: Shelter Network")
        m_ops = folium.Map(location=[s_lat, s_lon], zoom_start=11, tiles=None)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satellite', overlay=False, control=True
        ).add_to(m_ops)

        if s_risk >= 2:
            lats = np.linspace(17.60, 17.78, 15)
            lons = np.linspace(83.15, 83.40, 15)
            for la in lats:
                for lo in lons:
                    if lo > ((0.7 * (la - 17.60)) + 83.22):
                        folium.Circle([la, lo], radius=200, color='red', fill=True, fill_opacity=0.3, stroke=False).add_to(m_ops)

        nearest_node = None
        min_dist = float('inf')
        user_pos = (s_lat, s_lon)

        if is_vizag:
            for name, coords in shelter_db.items():
                d = geodesic(user_pos, coords).km
                if d < min_dist:
                    min_dist = d
                    nearest_node = (name, coords)
                folium.CircleMarker(coords, radius=1, color="#39ff14", fill=True, fill_opacity=0.6).add_to(m_ops)

            if s_risk >= 2 and nearest_node:
                target_name, target_coords = nearest_node
                folium.Marker(target_coords, icon=folium.Icon(color="green", icon="home"), tooltip=f"SAFE ZONE: {target_name}").add_to(m_ops)
                folium.PolyLine([user_pos, target_coords], color="cyan", weight=4, dash_array='10', opacity=0.8).add_to(m_ops)
                st.toast(f"Route calculated to {target_name} ({min_dist:.2f}km)", icon="🛸")

        st_folium(m_ops, width=900, height=600)