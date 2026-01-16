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
# 🔮 MODEL LOADING (FIXES SKLEARN ERROR)
# ==========================================
@st.cache_resource
def load_prediction_model():
    """Loads model with error trapping for missing libraries."""
    if not os.path.exists(MODEL_FILE):
        return None
    try:
        # This requires 'scikit-learn' in requirements.txt
        return joblib.load(MODEL_FILE)
    except ModuleNotFoundError:
        st.error("❌ Critical Error: 'scikit-learn' is not installed. System is in SOS-only mode.")
        return None
    except Exception as e:
        st.error(f"⚠️ Unexpected Error: {e}")
        return None

model = load_prediction_model()

# ==========================================
# 🆘 SOS CALL FUNCTION (DUAL FAILOVER)
# ==========================================
def make_sos_call(target_phone, lang):
    """Attempts call with primary account, fails over to secondary on Error 429."""
    audio_url = URL_TELUGU if lang == "Telugu" else URL_ENGLISH
    twiml = f'<Response><Play>{audio_url}</Play></Response>'
    
    last_err = ""
    for acc in ACCOUNTS:
        try:
            client = Client(acc["sid"], acc["token"])
            client.calls.create(twiml=twiml, to=target_phone, from_=acc["from"])
            return "SUCCESS"
        except Exception as e:
            last_err = str(e)
            # Continues to next account if Account 1 hits limits
            continue
    return f"Failed: {last_err}"

# ==========================================
# 📊 UI DISPLAY
# ==========================================
st.title("🌪️ Vizag Cyclone Command Center")

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
                    if status == "SUCCESS": 
                        st.success(f"✅ Call sent to {phone}")
                    else: 
                        # Shows the 429 error if both accounts are exhausted
                        st.error(f"❌ {phone}: {status}")

# Dashboard Columns
c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Location", "Visakhapatnam")
    if model:
        st.success("🤖 Prediction Model Active")
    else:
        st.warning("⚠️ Prediction Offline (Check requirements.txt)")

with c2:
    m = folium.Map(location=[17.68, 83.21], zoom_start=11)
    folium.Circle([17.68, 83.21], radius=15000, color='red', fill=True, popup="Risk Zone").add_to(m)
    st_folium(m, height=450, use_container_width=True)