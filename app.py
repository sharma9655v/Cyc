import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium

# ==========================================
# 🔑 CONFIGURATION & DIRECT LINKS
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
MODEL_FILE = "cyclone_model.joblib"

# Dual Twilio Accounts
ACCOUNTS = [
    {"sid": "ACc9b9941c778de30e2ed7ba57f87cdfbc", "token": "3cb1dfcb6a9a3cae88f4eff47e9458df", "from": "+15075195618"},
    {"sid": "ACa12e602647785572ebaf765659d26d23", "token": "26210979738809eaf59a678e98fe2c0f", "from": "+14176076960"}
]

# DIRECT GOOGLE DRIVE LINKS (Converted for Twilio access)
URL_ENGLISH = "https://drive.google.com/uc?export=download&id=1KKMmH10hPuqEc3-X8uAa7BLqlz5TzMdn"
URL_TELUGU = "https://drive.google.com/uc?export=download&id=18nSmhQKoV-Epc-e2qX9kvJyZkZaFB_X1"

st.set_page_config(page_title="Vizag Cyclone Command Center", layout="wide")

# ==========================================
# 🔮 MODEL LOADING (With Error Handling)
# ==========================================
@st.cache_resource
def load_prediction_model():
    if not os.path.exists(MODEL_FILE):
        return None
    try:
        # Requires 'scikit-learn' in requirements.txt
        return joblib.load(MODEL_FILE)
    except Exception as e:
        st.error(f"⚠️ Model Load Error: {e}")
        return None

model = load_prediction_model()

# ==========================================
# 🆘 SOS CALL FUNCTION
# ==========================================
def make_sos_call(target_phone, lang):
    audio_url = URL_TELUGU if lang == "Telugu" else URL_ENGLISH
    # Use <Play> to stream your specific Google Drive audio
    twiml = f'<Response><Play>{audio_url}</Play></Response>'
    
    last_err = ""
    for acc in ACCOUNTS:
        try:
            client = Client(acc["sid"], acc["token"])
            client.calls.create(twiml=twiml, to=target_phone, from_=acc["from"])
            return "SUCCESS"
        except Exception as e:
            last_err = str(e)
            continue
    return f"Failed: {last_err}"

# ==========================================
# 📊 UI DISPLAY
# ==========================================
st.title("🌪️ Vizag Cyclone Command Center")

if model is None:
    st.error("❌ Model not loaded. Please ensure 'scikit-learn' is in requirements.txt.")

with st.sidebar:
    st.header("🚨 Emergency SOS")
    num1 = st.text_input("Primary Contact", "+917678495189")
    num2 = st.text_input("Family Contact", "+918130631551")
    
    st.divider()
    lang = st.radio("Call Audio Language", ["English", "Telugu"])
    
    if st.button("🚨 TRIGGER SOS CALLS", type="primary", use_container_width=True):
        for phone in [num1, num2]:
            if len(phone) > 10:
                with st.spinner(f"Calling {phone}..."):
                    status = make_sos_call(phone, lang)
                    if status == "SUCCESS": st.success(f"✅ Call sent to {phone}")
                    else: st.error(f"❌ {phone}: {status}")

# Dashboard Columns
c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Location", "Visakhapatnam")
    # Live Weather logic would go here
    st.info("SOS system is ready with custom voice outputs.")

with c2:
    # Vizag Map View
    m = folium.Map(location=[17.68, 83.21], zoom_start=11)
    folium.Circle([17.68, 83.21], radius=15000, color='red', fill=True, popup="Risk Zone").add_to(m)
    st_folium(m, height=450, use_container_width=True)