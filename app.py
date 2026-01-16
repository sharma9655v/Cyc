import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
import random
import io
from geopy.distance import geodesic
from gtts import gTTS
import folium
from streamlit_folium import st_folium

# ==============================================================================
# MODULE 1: CONFIGURATION & STYLING
# ==============================================================================
CONFIG = {
    "APP_TITLE": "Vizag Cyclone Command Center",
    "API_KEY": "22223eb27d4a61523a6bbad9f42a14a7",
    "MODEL_PATH": "cyclone_model.joblib",
    "TARGET_CITY": "Visakhapatnam",
    "DEFAULT_COORDS": (17.6868, 83.2185) 
}

# Voice File Mapping (Links to your uploaded content)
VOICE_ASSETS = {
    "Broadcast Alert": "https://googleusercontent.com/file_content/36",
    "Detailed English Alert": "https://googleusercontent.com/file_content/35",
    "Telugu Emergency Alert": "https://googleusercontent.com/file_content/34",
    "Telugu Final Warning": "https://googleusercontent.com/file_content/37",
    "Standard Alert": "https://googleusercontent.com/file_content/33"
}

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .glass-card {
        background: rgba(30, 33, 48, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .emergency-banner {
        background: linear-gradient(90deg, #4a151b 0%, #2b0d10 100%);
        border-left: 5px solid #ff4b4b;
        color: #ff8080;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# MODULE 2: RECOVERY ENGINE & PREDICTION
# ==============================================================================
class PhysicsFallbackModel:
    def predict(self, X):
        pressure = X[0][2]
        if pressure < 960: return np.array([3])
        if pressure < 990: return np.array([2])
        if pressure < 1005: return np.array([1])
        return np.array([0])

@st.cache_resource
def load_cyclone_engine():
    if not os.path.exists(CONFIG["MODEL_PATH"]):
        return PhysicsFallbackModel(), True
    try:
        model = joblib.load(CONFIG["MODEL_PATH"])
        return model, False
    except Exception:
        return PhysicsFallbackModel(), True

model_engine, is_fallback = load_cyclone_engine()

# ==============================================================================
# MODULE 3: DATA & UTILITIES
# ==============================================================================
class CycloneUtils:
    @staticmethod
    @st.cache_data(ttl=3600)
    def get_shelters():
        hubs = {"Steel Plant": (17.63, 83.18), "Gajuwaka": (17.69, 83.21), "Port": (17.68, 83.28), "MVP": (17.74, 83.34)}
        network = {}
        for hub, coords in hubs.items():
            network[f"{hub} Main"] = coords
            for i in range(15):
                network[f"{hub} S-{i}"] = (coords[0]+random.uniform(-0.02,0.02), coords[1]+random.uniform(-0.02,0.02))
        return network

    @staticmethod
    def get_weather(city):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={CONFIG['API_KEY']}"
            r = requests.get(url, timeout=5).json()
            return r['coord']['lat'], r['coord']['lon'], r['main']['pressure'], r['name']
        except:
            return *CONFIG["DEFAULT_COORDS"], 1012, "Default (Simulated)"

utils = CycloneUtils()
shelter_db = utils.get_shelters()

# ==============================================================================
# MODULE 4: MAIN DASHBOARD
# ==============================================================================
st.title(f"🌪️ {CONFIG['APP_TITLE']}")

# Logic Calculations
lat, lon, pres, loc_name = utils.get_weather(CONFIG["TARGET_CITY"])
risk_level = int(model_engine.predict([[lat, lon, pres]])[0])

with st.sidebar:
    st.header("🎙️ Voice Dispatch Center")
    st.caption("Select a pre-recorded emergency note to play across the region.")
    
    selected_voice = st.selectbox("Select Audio Clip", list(VOICE_ASSETS.keys()))
    
    if st.button("🔊 Play Voice Dispatch"):
        st.audio(VOICE_ASSETS[selected_voice], format="audio/mp3", autoplay=True)
    
    st.divider()
    st.header("🌐 Regional Settings")
    city_query = st.text_input("Target City", CONFIG["TARGET_CITY"])

tab_live, tab_sim, tab_ops = st.tabs(["📡 Live Data", "🧪 Simulation", "🚨 Emergency Ops"])

# --- LIVE MONITOR ---
with tab_live:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f'<div class="glass-card"><h3>Live Pressure</h3><h1>{pres} hPa</h1></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card"><h3>Status</h3><h1>{["SAFE", "DEPRESSION", "STORM", "CYCLONE"][risk_level]}</h1></div>', unsafe_allow_html=True)
        
        # Auto-Play Alert Logic
        if risk_level >= 2:
            st.warning("🚨 HIGH RISK DETECTED")
            st.audio(VOICE_ASSETS["Broadcast Alert"], format="audio/mp3")

    with c2:
        m = folium.Map(location=[lat, lon], zoom_start=11)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)
        color = "red" if risk_level >= 2 else "cyan"
        folium.CircleMarker([lat, lon], radius=15, color=color, fill=True, popup=f"Risk: {risk_level}").add_to(m)
        st_folium(m, height=500, use_container_width=True)

# --- SIMULATION ---
with tab_sim:
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        s_pres = st.slider("Simulate Pressure (hPa)", 880, 1030, 970)
        s_risk = int(model_engine.predict([[lat, lon, s_pres]])[0])
        st.metric("Predicted Severity", f"Level {s_risk}")
        
        if s_risk >= 3:
            st.error("Extreme Cyclone Conditions Simulated")
            st.audio(VOICE_ASSETS["Telugu Final Warning"], format="audio/mp3")
            
    with sc2:
        st.write("Storm Intensity Progress Meter")
        st.progress(min(s_risk/3, 1.0))

# --- EMERGENCY OPS ---
with tab_ops:
    if risk_level >= 2:
        st.markdown('<div class="emergency-banner">🚨 EMERGENCY: Deploying Shelter Network.</div>', unsafe_allow_html=True)
        st.audio(VOICE_ASSETS["Telugu Emergency Alert"], format="audio/mp3")
    
    m_ops = folium.Map(location=[lat, lon], zoom_start=12)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m_ops)
    
    user_pos = (lat, lon)
    closest = sorted(shelter_db.items(), key=lambda x: geodesic(user_pos, x[1]).km)[:30]
    for name, coords in closest:
        folium.CircleMarker(coords, radius=4, color="#39ff14", fill=True, tooltip=name).add_to(m_ops)
    
    target_name, target_coords = closest[0]
    folium.PolyLine([user_pos, target_coords], color="cyan", weight=3, dash_array='5').add_to(m_ops)
    st.success(f"Route to nearest safe zone: {target_name}")
    st_folium(m_ops, height=500, use_container_width=True)