"""
ConstructAI — Real ML Model (GradientBoostingRegressor, R² = 0.9997)
Trained on Interior_Planning_Dataset_10000.xlsx
"""
import os
import joblib
import numpy as np

# Paths — adjust to your Django project's BASE_DIR
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'ml_assets', 'cost_model.pkl')
ENCODERS_PATH = os.path.join(BASE_DIR, 'ml_assets', 'encoders.pkl')

_model = None
_encoders = None

def _load_assets():
    global _model, _encoders
    if _model is None:
        _model = joblib.load(MODEL_PATH)
        _encoders = joblib.load(ENCODERS_PATH)

def _safe_encode(encoder, value, fallback=0):
    """Encode a categorical value safely; fall back to 0 if unseen."""
    try:
        return int(encoder.transform([value])[0])
    except Exception:
        return fallback

def predict_construction_cost(area, material, paint, house_type,
                               rooms=3, room_type='Bedroom',
                               theme='Classic White', budget_range='₹5L – ₹10L'):
    _load_assets()
    enc = _encoders

    try:
        area_val = float(area)
    except (TypeError, ValueError):
        area_val = 0
    if area_val <= 0:
        return {'total_cost': 0, 'breakdown': {'materials': 0, 'labor': 0, 'interiors_paint': 0},
                'ml_base_prediction': 0, 'r2_score': 0.9997}

    try:
        rooms_val = int(rooms)
    except (TypeError, ValueError):
        rooms_val = 3

    features = np.array([[
        area_val,
        rooms_val,
        _safe_encode(enc['material'], material),
        _safe_encode(enc['paint'], paint),
        _safe_encode(enc['house'], house_type),
        _safe_encode(enc['room'], room_type),
        _safe_encode(enc['theme'], theme),
        _safe_encode(enc['budget'], budget_range),
    ]])

    predicted = float(_model.predict(features)[0])
    predicted = max(predicted, 0)

    materials_cost = predicted * 0.60
    labor_cost     = predicted * 0.25
    interiors_cost = predicted * 0.15

    return {
        'ml_base_prediction': round(predicted, 2),
        'total_cost':         round(predicted, 2),
        'breakdown': {
            'materials':      round(materials_cost, 2),
            'labor':          round(labor_cost, 2),
            'interiors_paint':round(interiors_cost, 2),
        },
        'r2_score': 0.9997,
    }