# src/api.py - Backend API para la inferencia de modelos predictivos
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np
import os

app = FastAPI(
    title="Canarias Tourism AI API",
    description="API de Producción para predecir la ocupación turística en Canarias",
    version="1.0.0"
)

# Definir la estructura del vector de entrada
class PredictionFeatures(BaseModel):
    Month: int
    lag_1: float
    lag_2: float
    lag_12: float
    rolling_mean_3: float
    is_pandemic: int = 0

# Carga del modelo global
MODEL_PATH = "models/best_model_ocupacion.pkl"
FEATURES_PATH = "models/features_list.pkl"

model = None
features_list = None

def load_prediction_resources():
    global model, features_list
    if os.path.exists(MODEL_PATH) and os.path.exists(FEATURES_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            features_list = joblib.load(FEATURES_PATH)
            print("Modelo y variables cargadas con éxito en la API.")
        except Exception as e:
            print(f"Error cargando los recursos de machine learning: {e}")
    else:
        print("ADVERTENCIA: Recursos del modelo no encontrados en models/. ¿Has ejecutado src/train_models.py?")

# Carga inicial al arrancar
load_prediction_resources()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Bienvenido a la API de Inteligencia Turística de Canarias AI",
        "endpoints": {
            "/health": "Verificación de estado de la API y modelo",
            "/predict": "Inferencia de ocupación en formato JSON (POST)"
        }
    }

@app.get("/health")
def health_check():
    global model
    # Intentar re-cargar si es None
    if model is None:
        load_prediction_resources()
        
    if model is not None:
        return {"status": "healthy", "model_loaded": True}
    else:
        return {"status": "degraded", "model_loaded": False, "warning": "El archivo de modelo no se encuentra o no se puede cargar."}

@app.post("/predict")
def predict_occupancy(input_data: PredictionFeatures):
    global model, features_list
    if model is None:
        load_prediction_resources()
        if model is None:
            raise HTTPException(status_code=503, detail="El modelo no está disponible en el servidor.")
            
    try:
        # Convertir entrada en DataFrame
        X = pd.DataFrame([[
            input_data.Month,
            input_data.lag_1,
            input_data.lag_2,
            input_data.lag_12,
            input_data.rolling_mean_3,
            input_data.is_pandemic
        ]], columns=features_list)
        
        # Realizar inferencia
        prediction = float(np.clip(model.predict(X)[0], 0, 100))
        return {
            "success": True,
            "prediction_percentage": round(prediction, 2),
            "input_features": input_data.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno durante la inferencia: {str(e)}")
