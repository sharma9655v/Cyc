import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
import random
import time
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
from twilio.rest import Client # Ensure you run: pip install twilio

# --- CONFIGURATION ---
CONFIG = {
    "APP_TITLE": "Vizag Command Center",
    "API_KEY": "22223eb27d4a61523a6bbad9f42a14a7", 
    "MODEL_PATH": "cyclone_model.joblib",
    "TARGET_CITY": "Visakhapatnam",
    "DEFAULT_COORDS": (17.6868, 83.2185) 
}

# --- TWILIO FAILOVER CONFIGURATION ---
# Please replace these with your actual Twilio account details
TWILIO_ACCOUNTS = [
    {
        "name": "Primary",
        "sid": "ACc9b9941c778de30e2ed7ba57f87cdfbc",
        "token": "c9ec654e3d157bf4dfe1233e9001d7b1",
        "number": "+15075195618"
    },
    {
        "name": "Secondary",
        "sid": "ACa12e602647785572ebaf765659d26d23",
        "token": "3cde0a560ccaf8c60321a1e8bea5bb82",
        "number": "+14176076960"
    }
]

st.set_page_config(page_title=CONFIG["APP_TITLE"], page_icon="🌪️", layout="wide")

# --- SOS LOGIC (SMS + VOICE CALL) ---
def trigger_emergency_comms(location, risk_level, contact_number):
    """Sends SMS and triggers a Voice Call with automated speech."""
    sms_body = (
        f"⚠️ CYCLONE EMERGENCY ALERT ⚠️\n"
        f"Location: {location}\n"
        f"Risk Level: {risk_level}\n"
        f"Action: Evacuate to nearest shelter immediately."
    )
    
    twiml_content = f"""
    <Response>
        <Say voice="alice" language="en-IN">
            Attention. This is an automated emergency alert for {location}. 
            The cyclone risk is currently {risk_level}. 
            Please move to a safe zone or green shelter immediately.
        </Say>
    </Response>
    """

    for acc in TWILIO_ACCOUNTS:
        try:
            client = Client(acc["sid"], acc["token"])
            # 1. Send SMS
            client.messages.create(body=sms_body, from_=acc["number"], to=contact_number)
            # 2. Trigger Call
            client.calls.create(twiml=twiml_content, from_=acc["number"], to=contact_number)
            return f"Success: Alert and Call sent via {acc['name']}."
        except Exception as e:
            st.sidebar.warning(f"{acc['name']} failed: {str(e)}")
            continue
    return "Error: All SOS accounts failed."

# --- SESSION STATE ---
if 'reports' not in st.session_state:
    st.session_state['reports'] = []

# --- BACKEND ---
class DataManager:
    @staticmethod
    @st.cache_data(ttl=3600) 
    def fetch_shelter_network():
        hubs = {
            "Steel Plant Zone": (17.635, 83.180),
            "Gajuwaka": (17.690, 83.210),
            "MVP Colony": (17.740, 83.340),
            "Rushikonda": (17.780, 83.380)
        }
        network = {}
        for hub, (lat, lon) in hubs.items():
            for i in range(50): 
                d_lat = random.uniform(-0.02, 0.02)
                d_lon = random.uniform(-0.02, 0.02)
                network[f"{hub}_{i}"] = (lat + d_lat, lon + d_lon)
        return network

    @staticmethod
    def get_live_weather(city):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={CONFIG['API_KEY']}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200: return resp.json()
        except: return None
        return None

db = DataManager()
shelter_db = db.fetch_shelter_network()

# --- ML LOAD ---
if os.path.exists(CONFIG["MODEL_PATH"]):
    model = joblib.load(CONFIG["MODEL_PATH"])
else:
    st.warning("⚠️ Model not found. Using simulation mode.")
    class MockModel:
        def predict(self, x): return [2]
    model = MockModel()

def predict_risk(lat, lon, pressure):
    return model.predict([[lat, lon, pressure]])[0]

def simulate_future(pressure):
    times, risks = [], []
    curr_p = pressure
    for i in range(16): 
        times.append(f"T+{i*3}h")
        curr_p += random.randint(-5, 5) 
        risk = 0 if curr_p > 1000 else 1 if curr_p > 980 else 2 if curr_p > 920 else 3
        risks.append(risk)
    return pd.DataFrame({"Time": times, "Risk Level": risks})

# --- UI START ---
st.title(f"🌪️ {CONFIG['APP_TITLE']}")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚨 Emergency Control")
    
    # SOS SECTION
    st.subheader("Send Targeted SOS")
    target_number = st.text_input("Receiver Phone Number", placeholder="+91XXXXXXXXXX")
    
    if st.button("📢 TRIGGER SMS + CALL"):
        if not target_number:
            st.error("Please enter a number.")
        else:
            with st.spinner("Processing SOS..."):
                # Get current risk for accurate messaging
                w_current = db.get_live_weather(CONFIG["TARGET_CITY"])
                p_current = w_current['main']['pressure'] if w_current else 960
                risk_current = "CRITICAL" if p_current < 990 else "MODERATE"
                
                res = trigger_emergency_comms(CONFIG["TARGET_CITY"], risk_current, target_number)
                if "Success" in res:
                    st.success(res)
                else:
                    st.error(res)

    st.divider()
    st.error("📞 **Control Room: 1070**") 
    
    st.info("""
    **Quick Contacts:**
    * **NDRF:** 99999-99999
    * **Coast Guard:** 1554
    * **Ambulance:** 108
    """)
    
    st.divider()

    # REPORT INCIDENT FORM
    st.subheader("📢 Report Incident")
    with st.form("report_form"):
        incident_type = st.selectbox("Type", ["Tree Fallen", "Flooding", "Medical Emergency", "Road Blocked"])
        submit_report = st.form_submit_button("🚨 Submit Report")
        
        if submit_report:
            rand_lat = CONFIG["DEFAULT_COORDS"][0] + random.uniform(-0.05, 0.05)
            rand_lon = CONFIG["DEFAULT_COORDS"][1] + random.uniform(-0.05, 0.05)
            st.session_state['reports'].append({"type": incident_type, "lat": rand_lat, "lon": rand_lon})
            st.success("Report Submitted!")

# --- TABS ---
tab1, tab2 = st.tabs(["📊 Live Dashboard & Prediction", "🚨 Evacuation Map"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("📡 Current Status")
    w = db.get_live_weather(CONFIG["TARGET_CITY"])
    pres = w['main']['pressure'] if w else 1005
    lat, lon = (w['coord']['lat'], w['coord']['lon']) if w else CONFIG["DEFAULT_COORDS"]
    risk = predict_risk(lat, lon, pres)
    
    col1, col2 = st.columns(2)
    col1.metric("Live Pressure", f"{pres} hPa")
    col2.metric("Risk Level", "CRITICAL" if risk >= 2 else "NORMAL")

    st.divider()
    st.subheader("🔮 48-Hour Advance Prediction")
    sim_pres = st.slider("Simulate Future Pressure (hPa)", 880, 1050, 960)
    sim_data = simulate_future(sim_pres)
    st.line_chart(sim_data.set_index("Time"))

# --- TAB 2: MAP ---
with tab2:
    st.subheader("Risk Zones & Safe Shelters")
    m = folium.Map(location=[lat, lon], zoom_start=11)
    
    # Red Zones
    folium.Circle([17.65, 83.30], radius=3500, color="red", fill=True, fill_opacity=0.4, popup="High Risk").add_to(m)
    
    # Green Shelters
    for name, coords in shelter_db.items():
        folium.CircleMarker(coords, radius=2, color="green", fill=True, fill_opacity=0.7).add_to(m)
    
    # User Reports
    for report in st.session_state['reports']:
        folium.Marker(
            [report['lat'], report['lon']],
            popup=f"REPORT: {report['type']}",
            icon=folium.Icon(color="purple", icon="exclamation-sign")
        ).add_to(m)
        
    st_folium(m, height=500, width=800)