import pandas as pd
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "turismo_canarias")

def get_client():
    """Crea y devuelve el cliente de MongoDB Atlas."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Verificar conexion
        client.server_info()
        print(f"Conectado a MongoDB Atlas. Base de datos: {DB_NAME}")
        return client
    except errors.ServerSelectionTimeoutError as e:
        print(f"ERROR: No se pudo conectar a MongoDB Atlas. Comprueba la URI y la contraseña en .env")
        print(e)
        return None

def ingest_csv_to_mongo(client, csv_path, collection_name, batch_size=1000):
    """
    Ingesta un CSV limpio en una colección de MongoDB.
    - Convierte cada fila en un documento JSON.
    - Inserta en lotes (batch) para mayor eficiencia.
    - Elimina la colección existente antes de insertar (para idempotencia).
    """
    db = client[DB_NAME]
    collection = db[collection_name]

    print(f"\nCargando {csv_path} en colección '{collection_name}'...")
    df = pd.read_csv(csv_path, low_memory=False, dtype={"TERRITORIO_CODE": str})

    # Convertir la columna Date a string para compatibilidad con MongoDB
    if 'Date' in df.columns:
        df['Date'] = df['Date'].astype(str)

    # Reemplazar NaN con None para que MongoDB los ignore correctamente
    df = df.where(pd.notnull(df), None)

    # Eliminar datos anteriores de esta colección (para evitar duplicados al re-ejecutar)
    collection.drop()
    print(f"  Colección previa eliminada. Insertando {len(df)} documentos...")

    # Insertar en lotes
    records = df.to_dict(orient='records')
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        collection.insert_many(batch)

    # Crear índice en Date y TERRITORIO_CODE para optimizar consultas del modelo
    collection.create_index([("TERRITORIO_CODE", 1), ("Date", 1)])
    print(f"  OK: {len(records)} documentos insertados con índice creado.")

def main():
    client = get_client()
    if client is None:
        return

    processed_dir = "data/processed"

    datasets = {
        "hoteles_limpio.csv": "hoteles",
        "apartamentos_limpio.csv": "apartamentos",
        "viviendas_vacacionales_limpio.csv": "viviendas_vacacionales",
        "estrellas_3_limpio.csv": "establecimientos_3_estrellas",
    }

    for filename, collection_name in datasets.items():
        path = os.path.join(processed_dir, filename)
        if os.path.exists(path):
            ingest_csv_to_mongo(client, path, collection_name)
        else:
            print(f"Archivo no encontrado, omitiendo: {path}")

    client.close()
    print("\nIngesta completada. Conexión cerrada.")

if __name__ == "__main__":
    main()
