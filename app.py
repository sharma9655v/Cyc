import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
import random
import io
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
from twilio.rest import Client #

# ==============================================================================
# MODULE 1: CONFIGURATION & CREDENTIALS
# ==============================================================================
CONFIG = {
    "APP_TITLE": "Vizag Cyclone Command Center",
    "API_KEY": "22223eb27d4a61523a6bbad9f42a14a7",
    "MODEL_PATH": "cyclone_model.joblib",
    "TARGET_CITY": "Visakhapatnam",
    "DEFAULT_COORDS": (17.6868, 83.2185) 
}

# Your Twilio Credentials
TWILIO_ACCOUNTS = {
    "Primary": {
        "SID": "ACc9b9941c778de30e2ed7ba57f87cdfbc",
        "AUTH": "15173b1522f7711143c50e5ba0369856",
        "PHONE": "+15075195618"
    },
    "Backup": {
        "SID": "ACa12e602647785572ebaf765659d26d23",
        "AUTH": "9ddfac5b5499f2093b49c82c397380ca",
        "PHONE": "+14176076960"
    }
}

# Emergency Contact List (Add multiple numbers here)
EMERGENCY_CONTACTS = ["+91XXXXXXXXXX", "+91YYYYYYYYYY"] 

VOICE_MAP = {
    "📢 Regional Broadcast (English)": "alert_detailed.mp3",
    "🇮🇳 Emergency Alert (Telugu)": "alert_telugu_final.mp3"
}

VOICE_URLS = {
    "📢 Regional Broadcast (English)": "https://drive.google.com/uc?export=download&id=1CWswvjAoIAO7h6C6Jh-uCsrOWFM7dnS_",
    "🇮🇳 Emergency Alert (Telugu)": "https://drive.google.com/uc?export=download&id=15xz_g_TvMAF2Icjesi3FyMV6MMS-RZHt"
}

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

# ==============================================================================
# MODULE 2: VOICE & MESSAGE ENGINES
# ==============================================================================
def play_voice_file(file_name, autoplay=False):
    if os.path.exists(file_name):
        with open(file_name, "rb") as f:
            audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3", autoplay=autoplay)

def make_ai_voice_call(to_number, audio_url, account_key="Primary"):
    """Initiates a remote Twilio call with the AI voice."""
    try:
        acc = TWILIO_ACCOUNTS[account_key]
        client = Client(acc["SID"], acc["AUTH"])
        twiml = f'<Response><Play>{audio_url}</Play></Response>'
        call = client.calls.create(twiml=twiml, to=to_number, from_=acc["PHONE"])
        return True, call.sid
    except Exception as e:
        return False, str(e)

def silent_backend_sos(message_body, account_key="Primary"):
    """Sends SMS to all emergency contacts silently in the backend."""
    try:
        acc = TWILIO_ACCOUNTS[account_key]
        client = Client(acc["SID"], acc["AUTH"])
        for number in EMERGENCY_CONTACTS:
            client.messages.create(body=message_body, from_=acc["PHONE"], to=number)
        return True
    except:
        return False

# ==============================================================================
# MODULE 3: RECOVERY ENGINE & WEATHER
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
    except:
        return PhysicsFallbackModel(), True

model_engine, is_fallback = load_cyclone_engine()

def get_weather(city):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={CONFIG['API_KEY']}"
        r = requests.get(url, timeout=5).json()
        return r['coord']['lat'], r['coord']['lon'], r['main']['pressure'], r['name']
    except:
        return *CONFIG["DEFAULT_COORDS"], 1012, "Default (Simulated)"

# Logic Calculations
lat, lon, pres, loc_name = get_weather(CONFIG["TARGET_CITY"])
risk_level = int(model_engine.predict([[lat, lon, pres]])[0])

# Silent Automated Trigger
if risk_level >= 2:
    if 'auto_sos_sent' not in st.session_state:
        alert_body = f"AUTOMATED ALERT: High cyclone risk in {loc_name}. Pressure: {pres} hPa."
        silent_backend_sos(alert_body)
        st.session_state.auto_sos_sent = True

# ==============================================================================
# MODULE 4: UI LAYOUT
# ==============================================================================
st.title(f"🌪️ {CONFIG['APP_TITLE']}")

with st.sidebar:
    st.header("🎙️ Voice Dispatch Center")
    selected_voice = st.selectbox("Select Language Alert", list(VOICE_MAP.keys()))
    if st.button("🔊 Preview Voice locally"):
        play_voice_file(VOICE_MAP[selected_voice])
    st.divider()
    account_choice = st.radio("Twilio Account", ["Primary", "Backup"])

tab_live, tab_sim, tab_ops = st.tabs(["📡 Live Data Monitor", "🧪 Storm Simulation", "🚨 Emergency Ops"])

# --- LIVE MONITOR ---
with tab_live:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Live Pressure", f"{pres} hPa")
        st.metric("Current Region", loc_name)
        if risk_level >= 2:
            st.error("🚨 HIGH CYCLONE RISK DETECTED")

    with col2:
        m = folium.Map(location=[lat, lon], zoom_start=11)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)
        folium.CircleMarker([lat, lon], radius=15, color="red" if risk_level >= 2 else "cyan", fill=True).add_to(m)
        st_folium(m, height=500, use_container_width=True)

# --- EMERGENCY OPS ---
with tab_ops:
    st.header("🚨 Emergency Broadcast Center")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📞 Voice Dispatch")
        recipient = st.text_input("Target Number (+91...)", placeholder="+91XXXXXXXXXX")
        if st.button("Initiate AI Voice Call", type="primary"):
            success, result = make_ai_voice_call(recipient, VOICE_URLS[selected_voice], account_choice)
            if success: st.success(f"Call Initiated! SID: {result}")
            else: st.error(result)

    with col_b:
        st.subheader("📢 SOS Broadcast")
        sos_body = st.text_area("Manual SOS Message", f"URGENT: Cyclone Alert in {loc_name}. Pressure: {pres} hPa.")
        if st.button("Broadcast SOS SMS", type="secondary"):
            if silent_backend_sos(sos_body, account_choice):
                st.success(f"SOS Broadcasted to {len(EMERGENCY_CONTACTS)} contacts.")
            else: st.error("Broadcast Failed.")

# --- SIMULATION ---
with tab_sim:
    s_pres = st.slider("Simulate Low Pressure (hPa)", 880, 1030, 980)
    s_risk = int(model_engine.predict([[lat, lon, s_pres]])[0])
    st.metric("Predicted Severity", f"Level {s_risk}")