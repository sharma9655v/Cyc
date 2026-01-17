import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ==========================================
# 🔑 CONFIGURATION (2 TWILIO ACCOUNTS)
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Account 1 Credentials
TWILIO_SID_1 = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH_1 = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE_1 = "+15075195618"

# Account 2 Credentials (Backup)
TWILIO_SID_2 = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_2 = "26210979738809eaf59a678e98fe2c0f"
TWILIO_PHONE_2 = "+14176076960"

MODEL_FILE = "cyclone_model.joblib"
USERS_FILE = "users.csv"

# Check if at least one account is configured
SIMULATION_MODE = "YOUR_PRIMARY" in TWILIO_SID_1

st.set_page_config(page_title="Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🆘 SOS FUNCTION (DUAL ACCOUNT FAILOVER)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    if SIMULATION_MODE:
        return "SIMULATION"
    
    # 🛠️ DEBUGGED: Proper credential list for failover
    accounts = [
        {"sid": TWILIO_SID_1, "token": TWILIO_AUTH_1, "from": TWILIO_PHONE_1},
        {"sid": TWILIO_SID_2, "token": TWILIO_AUTH_2, "from": TWILIO_PHONE_2}
    ]
    
    last_error = ""
    for idx, acc in enumerate(accounts):
        try:
            # 🛠️ DEBUGGED: Validation to avoid 401 errors
            client = Client(acc["sid"].strip(), acc["token"].strip())
            
            # 1. SMS Alert
            client.messages.create(
                body=f"🚨 SOS: Cyclone Risk Detected!\nStatus: {label}\nLocation: {location}\nPressure: {pressure} hPa",
                from_=acc["from"],
                to=target_phone
            )
            
            # 2. Voice Alert (Hindi)
            call_content = f'<Response><Say language="hi-IN">Saavdhan! {location} mein chakravaat ka khatra hai. Kripya surakshit sthaan par jaye.</Say></Response>'
            client.calls.create(twiml=call_content, to=target_phone, from_=acc["from"])
            
            return "SUCCESS" 
        except Exception as e:
            last_error = str(e)
            # 🛠️ DEBUGGED: Only log the error and try the next account
            continue 
            
    return last_error

# ==========================================
# 🌪️ MODEL LOADING (DEBUGGED)
# ==========================================
@st.cache_resource
def load_prediction_model():
    """🛠️ DEBUGGED: Handles missing library errors"""
    if not os.path.exists(MODEL_FILE):
        return None
    try:
        return joblib.load(MODEL_FILE)
    except ModuleNotFoundError:
        st.error("❌ Missing Library: 'scikit-learn'. Add it to requirements.txt.")
        return None
    except Exception as e:
        st.error(f"❌ Load Error: {e}")
        return None

model = load_prediction_model()

# ==========================================
# 📊 SIDEBAR & DASHBOARD
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

with st.sidebar:
    st.header("Data Source")
    mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])
    st.divider()
    st.header("🚨 Emergency Contacts")
    p1 = st.sidebar.text_input("Primary Contact", "+917678495189")
    p2 = st.sidebar.text_input("Family Contact", "+918130631551")

# Logic Calculations
lat, lon, pres = 17.7, 83.3, 1012
loc_display = "Visakhapatnam"

if mode == "📡 Live Weather (API)":
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Visakhapatnam&appid={WEATHER_API_KEY}"
    try:
        res = requests.get(url).json()
        if res.get("cod") == 200:
            lat, lon, pres = res["coord"]["lat"], res["coord"]["lon"], res["main"]["pressure"]
            loc_display = res["name"]
    except: pass
else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012)
    loc_display = "Simulation Area"

# Prediction 
if model:
    prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
    current_status = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"][prediction_idx]
else:
    current_status = "⚠️ MODEL OFFLINE"
    prediction_idx = 0

# --- SOS BUTTON ---
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS NOW", use_container_width=True, type="primary"):
    targets = [p for p in [p1, p2] if len(p) > 10]
    for t in targets:
        with st.sidebar.spinner(f"Alerting {t}..."):
            status = trigger_sos(t, loc_display, pres, current_status)
            if status == "SUCCESS": st.sidebar.success(f"✅ Sent to {t}")
            else: st.sidebar.error(f"❌ {t}: {status}")

# --- DASHBOARD DISPLAY ---
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Pressure", f"{pres} hPa")
    st.markdown(f"### Status: {current_status}")

with c2:
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker([lat, lon], popup=loc_display).add_to(m)
    st_folium(m, width=700, height=450)