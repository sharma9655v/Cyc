import streamlit as st
import joblib
import numpy as np
import os
import requests
import folium
from streamlit_folium import st_folium
from twilio.rest import Client

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
        "AUTH": "15173b1522f7711143c50e5ba0369856",
        "PHONE": "+15075195618"
    },
    "Backup": {
        "SID": "ACa12e602647785572ebaf765659d26d23",
        "AUTH": "9ddfac5b5499f2093b49c82c397380ca",
        "PHONE": "+14176076960"
    }
}

# SOS CONTACTS - Add your emergency numbers here
SOS_CONTACTS = ["+91XXXXXXXXXX"] 

VOICE_CONFIG = {
    "📢 Regional Broadcast (English)": {
        "url": "https://drive.google.com/uc?export=download&id=1CWswvjAoIAO7h6C6Jh-uCsrOWFM7dnS_",
        "local": "alert_detailed.mp3"
    },
    "🇮🇳 Emergency Alert (Telugu)": {
        "url": "https://drive.google.com/uc?export=download&id=15xz_g_TvMAF2Icjesi3FyMV6MMS-RZHt",
        "local": "alert_telugu_final.mp3"
    }
}

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

# ==============================================================================
# MODULE 2: TWILIO ENGINES (Voice & SMS)
# ==============================================================================
def send_sos_sms(message_body, account_key="Primary"):
    """Sends automated SMS alerts to emergency contacts."""
    try:
        acc = TWILIO_ACCOUNTS[account_key]
        client = Client(acc["SID"], acc["AUTH"])
        results = []
        for number in SOS_CONTACTS:
            msg = client.messages.create(body=message_body, from_=acc["PHONE"], to=number)
            results.append(msg.sid)
        return True, results
    except Exception as e:
        return False, str(e)

def make_ai_voice_call(to_number, audio_url, account_key="Primary"):
    try:
        acc = TWILIO_ACCOUNTS[account_key]
        client = Client(acc["SID"], acc["AUTH"])
        twiml = f'<Response><Play>{audio_url}</Play></Response>'
        call = client.calls.create(twiml=twiml, to=to_number, from_=acc["PHONE"])
        return True, call.sid
    except Exception as e:
        return False, str(e)

def play_local_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/mp3")

# ==============================================================================
# MODULE 3: DATA & WEATHER
# ==============================================================================
def get_weather(city):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={CONFIG['API_KEY']}"
        r = requests.get(url, timeout=5).json()
        return r['coord']['lat'], r['coord']['lon'], r['main']['pressure'], r['name']
    except:
        return *CONFIG["DEFAULT_COORDS"], 1012, "Default (Simulated)"

lat, lon, pres, loc_name = get_weather(CONFIG["TARGET_CITY"])

# ==============================================================================
# MODULE 4: UI LAYOUT
# ==============================================================================
st.title(f"🌪️ {CONFIG['APP_TITLE']}")

with st.sidebar:
    st.header("⚙️ Dispatch Settings")
    selected_voice_label = st.selectbox("Select AI Voice Language", list(VOICE_CONFIG.keys()))
    account_choice = st.radio("Twilio Account", ["Primary", "Backup"])
    st.divider()
    st.subheader("🎙️ Local Voice Preview")
    play_local_audio(VOICE_CONFIG[selected_voice_label]["local"])

tab_live, tab_sim, tab_ops = st.tabs(["📡 Live Data Monitor", "🧪 Storm Simulation", "🚨 Emergency Ops"])

# --- LIVE MONITOR ---
with tab_live:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Live Pressure", f"{pres} hPa")
        st.metric("Region", loc_name)
        if pres < 1000:
            st.error("🚨 ALERT: Cyclone risk detected!")
            # Automated SOS Trigger
            if 'auto_sos_sent' not in st.session_state:
                alert_text = f"AUTOMATED SOS: Cyclone risk in {loc_name}. Pressure: {pres}hPa."
                send_sos_sms(alert_text, account_choice)
                st.session_state.auto_sos_sent = True

    with col2:
        m = folium.Map(location=[lat, lon], zoom_start=11)
        folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)
        folium.Marker([lat, lon], icon=folium.Icon(color='red', icon='warning', prefix='fa')).add_to(m)
        st_folium(m, height=500, use_container_width=True)

# --- EMERGENCY OPS ---
with tab_ops:
    st.header("🚨 Emergency Dispatch Center")
    c1, c2 = st.columns(2)
    with c1:
        recipient = st.text_input("Target Number (+91...)", placeholder="+91XXXXXXXXXX")
        if st.button("📞 Initiate AI Voice Call", type="primary"):
            success, result = make_ai_voice_call(recipient, VOICE_CONFIG[selected_voice_label]["url"], account_choice)
            st.success(f"Call SID: {result}") if success else st.error(result)
            
    with c2:
        sos_body = st.text_area("Manual SOS Message", f"URGENT: Cyclone Alert in {loc_name}. Current Pressure: {pres} hPa.")
        if st.button("📢 Broadcast SOS SMS", type="secondary"):
            success, sids = send_sos_sms(sos_body, account_choice)
            st.success(f"Sent {len(sids)} SOS alerts.") if success else st.error(sids)

# --- SIMULATION ---
with tab_sim:
    s_pres = st.slider("Simulate Pressure (hPa)", 880, 1030, 1010)
    st.metric("Risk Level", "High" if s_pres < 995 else "Normal")