# data_loader.py - Carga y cache de todos los datasets con integración a MongoDB Atlas y API FastAPI
import streamlit as st
import pandas as pd
import joblib
import os
import requests
from pymongo import MongoClient, errors
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "turismo_canarias")
API_URL = "http://localhost:8000"

def get_mongo_db():
    """Intenta conectar a MongoDB Atlas y devuelve la base de datos."""
    if not MONGO_URI:
        return None
    try:
        # Poner un timeout corto de 2.5 segundos para que la carga local no se congele si no hay internet
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2500)
        client.server_info() # Lanzará excepción si no hay conexión
        return client[DB_NAME]
    except Exception as e:
        print(f"MongoDB connection failed: {e}. Falling back to local CSV files.")
        return None

def check_api_health():
    """Verifica si la API en FastAPI está online."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=1.5)
        if response.status_code == 200 and response.json().get("status") == "healthy":
            return True
    except Exception:
        pass
    return False

@st.cache_data
def load_hoteles():
    db = get_mongo_db()
    if db is not None:
        try:
            print("Cargando datos de Hoteles desde MongoDB Atlas...")
            collection = db["hoteles"]
            cursor = collection.find({"MEDIDAS_CODE": "TASA_OCUPACION_HABITACION"})
            df = pd.DataFrame(list(cursor))
            if not df.empty:
                # Limpiar columnas de MongoDB
                if "_id" in df.columns:
                    df = df.drop(columns=["_id"])
                df["Date"] = pd.to_datetime(df["Date"])
                df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"])
                df["Year"] = df["Year"].astype(int)
                df["Month"] = df["Month"].astype(int)
                df["TERRITORIO_CODE"] = df["TERRITORIO_CODE"].astype(str).str.strip()
                return df.sort_values("Date").reset_index(drop=True)
        except Exception as e:
            print(f"Error cargando hoteles de Mongo: {e}. Usando CSV local...")
            
    # Fallback local
    print("Cargando hoteles desde CSV local...")
    df = pd.read_csv("data/processed/hoteles_limpio.csv", low_memory=False, dtype={"TERRITORIO_CODE": str})
    df["Date"] = pd.to_datetime(df["Date"])
    df["TERRITORIO_CODE"] = df["TERRITORIO_CODE"].astype(str).str.strip()
    df = df[df["MEDIDAS_CODE"] == "TASA_OCUPACION_HABITACION"].copy()
    return df.sort_values("Date").reset_index(drop=True)

@st.cache_data
def load_apartamentos():
    db = get_mongo_db()
    if db is not None:
        try:
            print("Cargando datos de Apartamentos desde MongoDB Atlas...")
            collection = db["apartamentos"]
            cursor = collection.find({"MEDIDAS_CODE": "TASA_OCUPACION_HABITACION"})
            df = pd.DataFrame(list(cursor))
            if not df.empty:
                if "_id" in df.columns:
                    df = df.drop(columns=["_id"])
                df["Date"] = pd.to_datetime(df["Date"])
                df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"])
                df["Year"] = df["Year"].astype(int)
                df["Month"] = df["Month"].astype(int)
                df["TERRITORIO_CODE"] = df["TERRITORIO_CODE"].astype(str).str.strip()
                return df.sort_values("Date").reset_index(drop=True)
        except Exception as e:
            print(f"Error cargando apartamentos de Mongo: {e}. Usando CSV local...")
            
    # Fallback local
    print("Cargando apartamentos desde CSV local...")
    df = pd.read_csv("data/processed/apartamentos_limpio.csv", low_memory=False, dtype={"TERRITORIO_CODE": str})
    df["Date"] = pd.to_datetime(df["Date"])
    df["TERRITORIO_CODE"] = df["TERRITORIO_CODE"].astype(str).str.strip()
    df = df[df["MEDIDAS_CODE"] == "TASA_OCUPACION_HABITACION"].copy()
    return df.sort_values("Date").reset_index(drop=True)

@st.cache_data
def load_viviendas():
    db = get_mongo_db()
    if db is not None:
        try:
            print("Cargando datos de Viviendas Vacacionales desde MongoDB Atlas...")
            collection = db["viviendas_vacacionales"]
            cursor = collection.find()
            df = pd.DataFrame(list(cursor))
            if not df.empty:
                if "_id" in df.columns:
                    df = df.drop(columns=["_id"])
                df["Date"] = pd.to_datetime(df["Date"])
                df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"])
                df["Year"] = df["Year"].astype(int)
                df["Month"] = df["Month"].astype(int)
                df["TERRITORIO_CODE"] = df["TERRITORIO_CODE"].astype(str).str.strip()
                return df.sort_values("Date").reset_index(drop=True)
        except Exception as e:
            print(f"Error cargando viviendas de Mongo: {e}. Usando CSV local...")
            
    # Fallback local
    print("Cargando viviendas vacacionales desde CSV local...")
    df = pd.read_csv("data/processed/viviendas_vacacionales_limpio.csv", low_memory=False, dtype={"TERRITORIO_CODE": str})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["TERRITORIO_CODE"] = df["TERRITORIO_CODE"].astype(str).str.strip()
    return df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

@st.cache_resource
def load_model():
    try:
        m = joblib.load("models/best_model_ocupacion.pkl")
        f = joblib.load("models/features_list.pkl")
        return m, f
    except Exception:
        return None, None

def query_api_prediction(month, lag_1, lag_2, lag_12, rolling_mean_3, is_pandemic=0):
    """Consulta la predicción a la API de FastAPI. Si falla, hace fallback local."""
    payload = {
        "Month": int(month),
        "lag_1": float(lag_1),
        "lag_2": float(lag_2),
        "lag_12": float(lag_12),
        "rolling_mean_3": float(rolling_mean_3),
        "is_pandemic": int(is_pandemic)
    }
    try:
        response = requests.post(f"{API_URL}/predict", json=payload, timeout=2.0)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result.get("prediction_percentage"), "API FastAPI (Producción)"
    except Exception as e:
        print(f"API request failed: {e}. Using local model fallback.")
        
    # Fallback local
    model, features_list = load_model()
    if model is not None:
        X = pd.DataFrame([[month, lag_1, lag_2, lag_12, rolling_mean_3, is_pandemic]], columns=features_list)
        pred = float(model.predict(X)[0])
        return min(max(pred, 0.0), 100.0), "Modelo Local (Fallback Offline)"
        
    return None, "Error: Sin modelo disponible"
