import streamlit as st
import joblib
import numpy as np
import os
import requests
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

# Mapping your uploaded files and the public Twilio links
VOICE_ASSETS = {
    "📢 Regional Broadcast (English)": {
        "local": "alert_detailed.mp3",
        "remote": "https://drive.google.com/uc?export=download&id=1CWswvjAoIAO7h6C6Jh-uCsrOWFM7dnS_"
    },
    "🇮🇳 Emergency Alert (Telugu)": {
        "local": "alert_telugu_final.mp3",
        "remote": "https://drive.google.com/uc?export=download&id=15xz_g_TvMAF2Icjesi3FyMV6MMS-RZHt"
    }
}

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

# ==============================================================================
# MODULE 2: DISPATCH ENGINE
# ==============================================================================
def dispatch_emergency_alert(to_number, asset_key, account_key="Primary"):
    """Plays audio locally on dashboard and triggers Twilio call."""
    try:
        asset = VOICE_ASSETS[asset_key]
        
        # 1. Local Playback (Left Side)
        if os.path.exists(asset["local"]):
            with open(asset["local"], "rb") as f:
                st.audio(f.read(), format="audio/mp3", autoplay=True)
        
        # 2. Remote Twilio Call
        acc = TWILIO_ACCOUNTS[account_key]
        client = Client(acc["SID"], acc["AUTH"])
        twiml = f'<Response><Play>{asset["remote"]}</Play></Response>'
        
        call = client.calls.create(twiml=twiml, to=to_number, from_=acc["PHONE"])
        return True, call.sid
    except Exception as e:
        return False, str(e)

# ==============================================================================
# MODULE 4: MAIN LAYOUT
# ==============================================================================
st.title(f"🌪️ {CONFIG['APP_TITLE']}")

# Real-time Weather Data Fetch
def get_weather(city):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={CONFIG['API_KEY']}"
        r = requests.get(url, timeout=5).json()
        return r['coord']['lat'], r['coord']['lon'], r['main']['pressure'], r['name']
    except:
        return *CONFIG["DEFAULT_COORDS"], 1012, "Default (Simulated)"

lat, lon, pres, loc_name = get_weather(CONFIG["TARGET_CITY"])

# --- SPLIT LAYOUT: Left (Voice/Metrics) | Right (Satellite Map) ---
left_col, right_col = st.columns([2, 3])

with left_col:
    st.header("🎙️ Voice Dispatch Center")
    st.markdown("---")
    
    # Emergency Controls
    selected_voice = st.selectbox("Select Alert Language", list(VOICE_ASSETS.keys()))
    acc_choice = st.radio("Route via Twilio Account", ["Primary", "Backup"], horizontal=True)
    recipient = st.text_input("Emergency Contact Number", placeholder="+91XXXXXXXXXX")
    
    if st.button("🔥 DISPATCH SIMULTANEOUS ALERTS", type="primary", use_container_width=True):
        if recipient:
            with st.spinner("Executing Dispatch..."):
                success, result = dispatch_emergency_alert(recipient, selected_voice, acc_choice)
                if success:
                    st.success(f"✅ Dispatched! Call SID: {result}")
                else:
                    st.error(f"❌ Error: {result}")
        else:
            st.warning("⚠️ Please provide a recipient number.")

    st.markdown("---")
    st.subheader("📊 Live Telemetry")
    st.metric("Atmospheric Pressure", f"{pres} hPa")
    st.metric("Target Zone", loc_name)

with right_col:
    st.header("📡 Satellite Surveillance")
    # Satellite Map Logic
    m = folium.Map(location=[lat, lon], zoom_start=11)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite'
    ).add_to(m)
    
    # Add status marker
    folium.Marker(
        [lat, lon], 
        popup="Cyclone Center",
        icon=folium.Icon(color="red", icon="warning", prefix="fa")
    ).add_to(m)
    
    st_folium(m, height=550, use_container_width=True)