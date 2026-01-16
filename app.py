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
# MODULE 1: CONFIGURATION & VOICE ASSETS
# ==============================================================================
CONFIG = {
    "APP_TITLE": "Vizag Cyclone Command Center",
    "API_KEY": "22223eb27d4a61523a6bbad9f42a14a7",
    "MODEL_PATH": "cyclone_model.joblib",
    "TARGET_CITY": "Visakhapatnam",
    "DEFAULT_COORDS": (17.6868, 83.2185) 
}

# Mapping your uploaded ContentFetchIDs to specific roles
VOICE_MAP = {
    "📢 Regional Broadcast": "uploaded:alert_broadcast.mp3",
    "🇮🇳 Telugu Emergency": "uploaded:alert_telugu.mp3",
    "🚩 Final Telugu Warning": "uploaded:alert_telugu_final.mp3",
    "🇬🇧 English Detailed": "uploaded:alert_detailed.mp3",
    "⚠️ Standard Alert": "uploaded:alert.mp3"
}

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

# (Styling remains the same as your provided code)
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# MODULE 2: RECOVERY ENGINE
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

with st.sidebar:
    st.header("🎙️ Voice Dispatch Console")
    st.caption("Select a high-quality voice note to play:")
    
    # Dropdown to select your uploaded voice notes
    selected_voice_label = st.selectbox("Choose Audio Note", list(VOICE_MAP.keys()))
    
    if st.button("🔊 Play Selected Dispatch"):
        # This plays the file directly from your uploaded ContentFetchID
        st.audio(VOICE_MAP[selected_voice_label], format="audio/mp3")
    
    st.divider()
    st.header("🌐 Regional Settings")
    city_query = st.text_input("Target City", CONFIG["TARGET_CITY"])

tab_live, tab_sim, tab_ops = st.tabs(["📡 Live Data", "🧪 Simulation", "🚨 Emergency Ops"])

# LOGIC CALCULATIONS
lat, lon, pres, loc_name = utils.get_weather(city_query)
risk_level = int(model_engine.predict([[lat, lon, pres]])[0])

# --- LIVE MONITOR ---
with tab_live:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f'<div class="glass-card"><h3>Live Pressure</h3><h1>{pres} hPa</h1></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="glass-card"><h3>Risk Level</h3><h1>{["SAFE", "DEPRESSION", "STORM", "CYCLONE"][risk_level]}</h1></div>', unsafe_allow_html=True)
        
        # Automatic trigger: If status is STORM or CYCLONE, play the Broadcast note
        if risk_level >= 2:
            st.error("🚨 CRITICAL RISK DETECTED")
            st.audio(VOICE_MAP["📢 Regional Broadcast"], format="audio/mp3")

    with c2:
        m = folium.Map(location=[lat, lon], zoom_start=11)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)
        folium.CircleMarker([lat, lon], radius=15, color="red" if risk_level >= 2 else "cyan", fill=True).add_to(m)
        st_folium(m, height=500, use_container_width=True)

# --- SIMULATION ---
with tab_sim:
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        s_pres = st.slider("Simulate Pressure (hPa)", 880, 1030, 970)
        s_risk = int(model_engine.predict([[lat, lon, s_pres]])[0])
        st.metric("Predicted Severity", f"Level {s_risk}")
        
        # Play the Final Telugu Warning if extreme pressure is simulated
        if s_risk == 3:
            st.audio(VOICE_MAP["🚩 Final Telugu Warning"], format="audio/mp3")
            
    with sc2:
        st.progress(min(s_risk/3, 1.0))

# --- EMERGENCY OPS ---
with tab_ops:
    if risk_level >= 2:
        st.audio(VOICE_MAP["🇮🇳 Telugu Emergency"], format="audio/mp3")
        st.markdown('<div class="emergency-banner">🚨 EMERGENCY: High Risk. Deploying Shelter Network.</div>', unsafe_allow_html=True)
    
    # (Shelter routing map remains the same)
    user_pos = (lat, lon)
    closest = sorted(shelter_db.items(), key=lambda x: geodesic(user_pos, x[1]).km)[:30]
    m_ops = folium.Map(location=[lat, lon], zoom_start=12)
    for name, coords in closest:
        folium.CircleMarker(coords, radius=4, color="#39ff14", fill=True, tooltip=name).add_to(m_ops)
    st_folium(m_ops, height=500, use_container_width=True)