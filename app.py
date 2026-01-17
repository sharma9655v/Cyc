import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
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
    "DEFAULT_COORDS": [17.6868, 83.2185] 
}

# Twilio Credentials
TWILIO_ACCOUNTS = {
    "Primary": {
        "SID": "ACc9b9941c778de30e2ed7ba57f87cdfbc",
        "AUTH": "3cb1dfcb6a9a3cae88f4eff47e9458df",
        "PHONE": "+15075195618"
    },
    "Backup": {
        "SID": "ACa12e602647785572ebaf765659d26d23",
        "AUTH": "6460cb8dfe71e335741bb20bc14c452a",
        "PHONE": "+14176076960"
    }
}

# AI Voice Assets (Converted to Direct Download Links for Twilio)
VOICE_MAP = {
    "📢 Regional Broadcast (English)": "https://drive.google.com/uc?export=download&id=1CWswvjAoIAO7h6C6Jh-uCsrOWFM7dnS_",
    "🇮🇳 Emergency Alert (Telugu)": "https://drive.google.com/uc?export=download&id=15xz_g_TvMAF2Icjesi3FyMV6MMS-RZHt"
}

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

# ==============================================================================
# MODULE 2: EMERGENCY SERVICES (TWILIO)
# ==============================================================================
def trigger_voice_call(to_number, audio_url, account_key="Primary"):
    """Initiates an outbound call playing the custom AI voice via Twilio."""
    try:
        acc = TWILIO_ACCOUNTS[account_key]
        client = Client(acc["SID"], acc["AUTH"])
        
        # TwiML logic to play the hosted MP3
        twiml_content = f'<Response><Play>{audio_url}</Play></Response>'
        
        call = client.calls.create(
            twiml=twiml_content,
            to=to_number,
            from_=acc["PHONE"]
        )
        return True, call.sid
    except Exception as e:
        return False, str(e)

# ==============================================================================
# MODULE 3: CYCLONE ENGINE & WEATHER
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
        # Requires 'scikit-learn' in requirements.txt
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

# ==============================================================================
# MODULE 4: DASHBOARD UI
# ==============================================================================
st.title(f"🌪️ {CONFIG['APP_TITLE']}")

# Real-time Logic
lat, lon, pres, loc_name = get_weather(CONFIG["TARGET_CITY"])
risk_level = int(model_engine.predict([[lat, lon, pres]])[0])

with st.sidebar:
    st.header("🎙️ Voice Dispatch Center")
    selected_voice = st.selectbox("Select Language Alert", list(VOICE_MAP.keys()))
    
    if st.button("🔊 Preview Audio in Browser"):
        st.audio(VOICE_MAP[selected_voice], format="audio/mp3")
    
    st.divider()
    account_choice = st.radio("Twilio Account", ["Primary", "Backup"])

tab_live, tab_sim, tab_ops = st.tabs(["📡 Live Data Monitor", "🧪 Storm Simulation", "🚨 Emergency Ops"])

# --- LIVE MONITOR ---
with tab_live:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Live Pressure", f"{pres} hPa")
        st.metric("Location", loc_name)
        if risk_level >= 2:
            st.error("🚨 HIGH CYCLONE RISK DETECTED")

    with col2:
        # Satellite Map Implementation
        m = folium.Map(location=[lat, lon], zoom_start=10)
        
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)

        folium.Marker(
            [lat, lon], 
            popup=f"Status: Level {risk_level} Risk",
            icon=folium.Icon(color='red' if risk_level >= 2 else 'blue', icon='info-sign')
        ).add_to(m)

        st_folium(m, height=500, use_container_width=True)

# --- EMERGENCY OPS (TWILIO CALLING) ---
with tab_ops:
    st.header("🚨 AI Voice Call Dispatch")
    st.write("Enter a phone number to trigger an AI voice alert via Twilio.")
    
    recipient = st.text_input("Recipient Phone Number (e.g., +91XXXXXXXXXX)")
    
    if st.button("📞 Trigger Emergency Call", type="primary"):
        if recipient:
            with st.spinner("Connecting to Twilio..."):
                success, result = trigger_voice_call(recipient, VOICE_MAP[selected_voice], account_choice)
                if success:
                    st.success(f"✅ Call Initiated! SID: {result}")
                else:
                    st.error(f"❌ Failed: {result}")
        else:
            st.warning("Please enter a phone number.")

# --- SIMULATION ---
with tab_sim:
    s_pres = st.slider("Simulate Low Pressure (hPa)", 880, 1030, 970)
    s_risk = int(model_engine.predict([[lat, lon, s_pres]])[0])
    st.progress(min(s_risk/3, 1.0))
    st.subheader(f"Simulated Risk: Level {s_risk}")