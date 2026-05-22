# src/download_municipios_geojson.py - Descarga y procesa las fronteras municipales de Canarias desde ISTAC
import json
import urllib.request
import os

def download_and_process_municipios():
    url = "https://datos.canarias.es/catalogos/estadisticas/dataset/6dd8baf4-14f4-43a3-88b2-984d034c965c/resource/812f22ae-62a5-4cea-8052-b0269b1bd491/download/municipios_desde2007_20170101.json"
    output_path = "data/processed/canarias_municipios.geojson"
    
    print(f"Descargando municipios de Canarias desde ISTAC: {url}...")
    try:
        # Poner un User-Agent por si acaso el servidor de ISTAC bloquea llamadas básicas de Python
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        print("Descarga completada. Analizando estructura del primer municipio...")
        features = data.get("features", [])
        if not features:
            print("Error: El GeoJSON descargado no contiene features.")
            return False
            
        # Inspeccionar propiedades de la primera feature para identificar el código municipal de 5 dígitos
        first_feat = features[0]
        props = first_feat.get("properties", {})
        print("Propiedades disponibles en el primer elemento:")
        for k, v in props.items():
            print(f"  - {k}: {v}")
            
        # Determinar cuál es la propiedad que contiene el código INE de 5 dígitos (suele llamarse 'codigo' o 'código' o 'id' o 'clave')
        code_key = None
        for key in ["codigo", "código", "clave", "id", "cod_muni", "CODMUNI", "cod_municipio"]:
            if key in props:
                code_key = key
                break
                
        if not code_key:
            # Si no está en propiedades, buscar en las claves directamente si es string
            print("Advertencia: No se detectó clave obvia en properties. Intentando mapeo automático...")
            # Usar la primera clave en properties que tenga longitud 5 y sea numérica como fallback
            for k, v in props.items():
                if isinstance(v, str) and len(v) == 5 and v.isdigit():
                    code_key = k
                    print(f"  -> Usando fallback de propiedad: '{code_key}' (valor: {v})")
                    break
        
        # Si sigue sin encontrarse, usar 'id' directo de la feature si existe
        if not code_key and "id" in first_feat:
            print("  -> Usando fallback de ID de feature")
            
        # Procesar y limpiar las features
        cleaned_features = []
        for feature in features:
            properties = feature.get("properties", {})
            
            # Obtener el código de 5 dígitos
            muni_code = None
            if code_key and code_key in properties:
                muni_code = str(properties[code_key])
            elif "id" in feature:
                muni_code = str(feature["id"])
                
            if not muni_code:
                continue
                
            # Limpiar para que tenga exactamente 5 caracteres (por ejemplo, a veces viene con decimales o espacios)
            muni_code = muni_code.strip().split(".")[0]
            if len(muni_code) == 4:
                # Corregir si le falta el cero a la izquierda (por ejemplo, Almería u otros, aunque en Canarias empiezan por 35 y 38)
                muni_code = "0" + muni_code
                
            # Solo nos interesan los códigos de las provincias de Las Palmas (35xxx) y S.C. Tenerife (38xxx)
            if not (muni_code.startswith("35") or muni_code.startswith("38")):
                continue
                
            # Sobrescribir o añadir la propiedad 'MUNI_CODE' estandarizada para facilitar el mapeo en Plotly
            properties["MUNI_CODE"] = muni_code
            feature["properties"] = properties
            cleaned_features.append(feature)
            
        # Crear el GeoJSON final
        canarias_municipios = {
            "type": "FeatureCollection",
            "features": cleaned_features
        }
        
        # Guardar en local
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(canarias_municipios, f, ensure_ascii=False, indent=2)
            
        print(f"¡Éxito! Archivo guardado localmente en: {output_path}")
        print(f"Número de municipios de Canarias extraídos y limpios: {len(cleaned_features)}")
        return True
    except Exception as e:
        print(f"Error descargando o procesando GeoJSON de municipios: {e}")
        return False

if __name__ == "__main__":
    download_and_process_municipios()
