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

# Account 1 Credentials
TWILIO_SID_1 = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH_1 = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE_1 = "+15075195618"

# Account 2 Credentials (Backup)
TWILIO_SID_2 = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_2 = "26210979738809eaf59a678e98fe2c0f"
TWILIO_PHONE_2 = "+14176076960"

# --- PUBLIC MP3 LINKS (Twilio must be able to reach these online) ---
# Replace these with the actual public URLs you generated for your files
URL_ENGLISH_MP3 = "https://your-public-link.com/alert_detailed.mp3"
URL_TELUGU_MP3 = "https://your-public-link.com/alert_telugu_final.mp3"

MODEL_FILE = "cyclone_model.joblib"

st.set_page_config(page_title="Vizag SOS Dual-Link", page_icon="🌪️", layout="wide")

# ==============================================================================
# 🆘 SOS FUNCTION (DUAL ACCOUNT FAILOVER)
# ==============================================================================
def trigger_sos_dual(target_phone, language="English"):
    # List of accounts to try in order
    accounts = [
        {"sid": TWILIO_SID_1, "token": TWILIO_AUTH_1, "from": TWILIO_PHONE_1},
        {"sid": TWILIO_SID_2, "token": TWILIO_AUTH_2, "from": TWILIO_PHONE_2}
    ]
    
    audio_url = URL_TELUGU_MP3 if language == "Telugu" else URL_ENGLISH_MP3
    twiml_content = f'<Response><Play>{audio_url}</Play></Response>'
    
    last_error = ""
    for idx, acc in enumerate(accounts):
        try:
            client = Client(acc["sid"], acc["token"])
            client.calls.create(
                twiml=twiml_content,
                to=target_phone,
                from_=acc["from"]
            )
            return f"SUCCESS (Account {idx+1})" # Stop if the first account works
        except Exception as e:
            last_error = str(e)
            continue # Try the next account if this one fails
            
    return f"FAILED BOTH ACCOUNTS: {last_error}"

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
        return 17.68, 83.21, 1012 

lat, lon, pres = get_live_weather()
prediction_idx = 0
if model:
    prediction_idx = int(model.predict(np.array([[lat, lon, pres]]))[0])

# ==============================================================================
# 📊 DASHBOARD UI
# ==============================================================================
st.title("🌪️ Vizag Cyclone Command Center (Dual SOS)")

with st.sidebar:
    st.header("🚨 Emergency Contacts")
    c1 = st.text_input("Primary Contact", "+917678495189")
    c2 = st.text_input("Family Contact", "+918130631551")
    
    st.divider()
    st.subheader("Broadcast Audio")
    call_lang = st.radio("Select MP3 Language", ["English", "Telugu"])
    
    if st.button("🚨 TRIGGER DUAL-ACCOUNT SOS", type="primary", use_container_width=True):
        for t in [c1, c2]:
            if len(t) > 10:
                with st.spinner(f"Initiating call to {t}..."):
                    result = trigger_sos_dual(t, call_lang)
                    if "SUCCESS" in result:
                        st.success(f"✅ {t}: {result}")
                    else:
                        st.error(f"❌ {t}: {result}")

# Main Dashboard
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Live Pressure", f"{pres} hPa")
    status = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"][prediction_idx]
    st.subheader(f"Status: {status}")
    
    st.divider()
    st.write("🔊 **Local MP3 Preview**")
    if os.path.exists("alert_detailed.mp3"):
        st.audio("alert_detailed.mp3")
    if os.path.exists("alert_telugu_final.mp3"):
        st.audio("alert_telugu_final.mp3")

with col2:
    m = folium.Map(location=[lat, lon], zoom_start=11)
    folium.Circle([lat, lon], radius=15000, color='red', fill=True, popup="Risk Zone").add_to(m)
    st_folium(m, height=450, use_container_width=True)