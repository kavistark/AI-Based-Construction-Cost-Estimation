"""
ConstructAI — One-time Model Training Script
Run this ONCE to train the model from your dataset.
Place this script at the root of your Django project.

Usage:
    python train_and_save_model.py

This creates:
    <your_app>/ml_assets/cost_model.pkl
    <your_app>/ml_assets/encoders.pkl
"""
import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import joblib
import json

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATASET_PATH = 'Interior_Planning_Dataset_10000.xlsx'   # adjust path if needed
APP_NAME     = 'estimator'   # your Django app folder name
OUTPUT_DIR   = os.path.join(APP_NAME, 'ml_assets')
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading dataset...")
df = pd.read_excel(DATASET_PATH, header=1)
print(f"  Rows: {len(df)} | Columns: {df.columns.tolist()}")

# Encode categoricals
encoders = {}
for col, key in [
    ('Material_Quality',    'material'),
    ('Paint_Type',          'paint'),
    ('House_Type',          'house'),
    ('Room_Type_Interior',  'room'),
    ('Preferred_Color_Theme','theme'),
    ('Budget_Range',        'budget'),
]:
    le = LabelEncoder()
    df[f'{key}_enc'] = le.fit_transform(df[col])
    encoders[key] = le

features = ['Plot_Area_sqft','Number_of_Rooms','material_enc','paint_enc',
            'house_enc','room_enc','theme_enc','budget_enc']
X = df[features]
y = df['Estimated_Cost_INR']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training GradientBoostingRegressor (n_estimators=200)…")
model = GradientBoostingRegressor(n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
mae  = mean_absolute_error(y_test, y_pred)
r2   = r2_score(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"\n  R²   = {r2:.6f}")
print(f"  MAE  = ₹{mae:,.0f}")
print(f"  RMSE = ₹{rmse:,.0f}")

model_path    = os.path.join(OUTPUT_DIR, 'cost_model.pkl')
encoders_path = os.path.join(OUTPUT_DIR, 'encoders.pkl')
joblib.dump(model,    model_path)
joblib.dump(encoders, encoders_path)
print(f"\nSaved model    → {model_path}")
print(f"Saved encoders → {encoders_path}")

mapping = {k: v.classes_.tolist() for k, v in encoders.items()}
mapping['metrics'] = {'mae': float(mae), 'r2': float(r2), 'rmse': float(rmse)}
with open(os.path.join(OUTPUT_DIR, 'model_mapping.json'), 'w', encoding='utf-8') as f:
    json.dump(mapping, f, indent=2, ensure_ascii=False)
print("Saved mapping  →", os.path.join(OUTPUT_DIR, 'model_mapping.json'))
print("\nDone! Your app is ready.")