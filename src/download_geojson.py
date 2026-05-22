# src/download_geojson.py - Descarga y filtra las fronteras geográficas de las islas de Canarias
import json
import urllib.request
import os

def download_and_filter_geojson():
    geojson_url = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326.geojson"
    output_path = "data/processed/canarias_islas.geojson"
    
    # Asegurar que el directorio de salida existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Descargando NUTS de Eurostat desde: {geojson_url}...")
    try:
        with urllib.request.urlopen(geojson_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        print("Filtrando NUTS3 para las 7 Islas Canarias (ES70)...")
        # Filtrar solo elementos de nivel NUTS3 que pertenecen a Canarias (empiezan por ES70)
        filtered_features = []
        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            nuts_id = properties.get("NUTS_ID", "")
            levl_code = properties.get("LEVL_CODE", -1)
            
            # ES703, ES704, ES705, ES706, ES707, ES708, ES709
            if nuts_id.startswith("ES70") and levl_code == 3:
                filtered_features.append(feature)
                
        # Crear un nuevo GeoJSON limpio
        canarias_geojson = {
            "type": "FeatureCollection",
            "features": filtered_features
        }
        
        # Guardar en local
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(canarias_geojson, f, ensure_ascii=False, indent=2)
            
        print(f"¡Éxito! Archivo guardado localmente en: {output_path}")
        print(f"Número de islas extraídas: {len(filtered_features)}")
        return True
    except Exception as e:
        print(f"Error descargando o procesando GeoJSON: {e}")
        return False

if __name__ == "__main__":
    download_and_filter_geojson()
