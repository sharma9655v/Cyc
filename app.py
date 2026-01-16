import streamlit as st
import joblib
import numpy as np
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium

# ==============================================================================
# 🔑 CONFIGURATION
# ==============================================================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Twilio Credentials
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE = "+15075195618"

# --- PASTE YOUR PUBLIC MP3 LINKS HERE ---
# These must be direct links that end in .mp3
URL_ENGLISH_MP3 = "REPLACE_WITH_YOUR_ENGLISH_PUBLIC_URL"
URL_TELUGU_MP3 = "REPLACE_WITH_YOUR_TELUGU_PUBLIC_URL"

MODEL_FILE = "cyclone_model.joblib"

st.set_page_config(page_title="Vizag SOS Center", page_icon="🌪️", layout="wide")

# ==============================================================================
# 🆘 SOS FUNCTION (CALL WITH YOUR MP3)
# ==============================================================================
def trigger_sos_call(target_phone, language="English"):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        
        # Select the hosted URL provided by the user
        audio_url = URL_TELUGU_MP3 if language == "Telugu" else URL_ENGLISH_MP3
        
        # Use <Play> to stream the MP3 file during the call
        twiml_content = f'<Response><Play>{audio_url}</Play></Response>'
        
        client.calls.create(
            twiml=twiml_content,
            to=target_phone,
            from_=TWILIO_PHONE
        )
        return "SUCCESS"
    except Exception as e:
        return str(e)

# ==============================================================================
# 🌪️ WEATHER & PREDICTION LOGIC
# ==============================================================================
@st.cache_resource
def load_model():
    if os.path.exists(MODEL_FILE):
        return joblib.load(MODEL_FILE)
    return None

model = load_model()

def get_live_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Visakhapatnam&appid={WEATHER_API_KEY}"
    try:
        res = requests.get(url).json()
        return res["coord"]["lat"], res["coord"]["lon"], res["main"]["pressure"]
    except:
        return 17.68, 83.21, 1012 # Default Vizag coordinates

lat, lon, pres = get_live_weather()
prediction_idx = 0
if model:
    prediction_idx = int(model.predict(np.array([[lat, lon, pres]]))[0])

# ==============================================================================
# 📊 DASHBOARD UI
# ==============================================================================
st.title("🌪️ Vizag Cyclone Command Center")

with st.sidebar:
    st.header("🚨 Emergency Dispatch")
    contact1 = st.text_input("Primary Contact", "+917678495189")
    contact2 = st.text_input("Family Contact", "+918130631551")
    
    st.divider()
    st.subheader("Choose Audio Language")
    call_lang = st.radio("Broadcast Language", ["English", "Telugu"])
    
    if st.button("🚨 TRIGGER SOS CALLS", type="primary", use_container_width=True):
        for t in [contact1, contact2]:
            if len(t) > 10:
                with st.spinner(f"Calling {t}..."):
                    res = trigger_sos_call(t, call_lang)
                    if res == "SUCCESS": st.success(f"✅ Call sent to {t}")
                    else: st.error(f"❌ {t}: {res}")

# Main Dashboard Content
c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Live Pressure", f"{pres} hPa")
    status = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"][prediction_idx]
    st.subheader(f"Status: {status}")
    
    # Local Audio Preview
    st.divider()
    st.write("🔊 **Preview Local Voice Notes**")
    if os.path.exists("alert_detailed.mp3"):
        st.audio("alert_detailed.mp3") # English file
    if os.path.exists("alert_telugu_final.mp3"):
        st.audio("alert_telugu_final.mp3") # Telugu file

with c2:
    m = folium.Map(location=[lat, lon], zoom_start=11)
    folium.Marker([lat, lon], popup="Vizag Center").add_to(m)
    folium.Circle([lat, lon], radius=15000, color='red', fill=True).add_to(m)
    st_folium(m, height=450, use_container_width=True)