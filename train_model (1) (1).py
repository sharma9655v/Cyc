import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import random

print("⏳ Generating Cyclone AI Model...")

# 1. Generate Synthetic Training Data
# Logic: Lower Pressure + Specific Lat/Lon = Higher Risk
data = []
for _ in range(5000):
    lat = random.uniform(10.0, 25.0)  
    lon = random.uniform(80.0, 95.0)  
    pressure = random.uniform(880, 1050) # hPa
    
    # Define Risk Rules for Training
    if pressure < 920:
        risk = 3 # Severe
    elif pressure < 980:
        risk = 2 # Warning
    elif pressure < 1005:
        risk = 1 # Watch
    else:
        risk = 0 # Normal
        
    data.append([lat, lon, pressure, risk])

# 2. Train the Model
df = pd.DataFrame(data, columns=['lat', 'lon', 'pressure', 'risk'])
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(df[['lat', 'lon', 'pressure']], df['risk'])

# 3. Save the File
joblib.dump(model, 'cyclone_model.joblib')
print("✅ SUCCESS! 'cyclone_model.joblib' has been created.")