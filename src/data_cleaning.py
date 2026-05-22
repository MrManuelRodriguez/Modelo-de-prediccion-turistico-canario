import pandas as pd
import numpy as np
import os
import glob

def clean_istac_csv(file_path):
    """
    Limpia un archivo CSV estándar de ISTAC aplicando la metodología aprobada:
    1. Estandarización de cabeceras.
    2. Filtrado de datos mensuales.
    3. Tratamiento de nulos e imputación.
    4. Creación de variables de fecha y pandemia.
    """
    print(f"Procesando: {file_path}")
    
    try:
        df = pd.read_csv(file_path, sep=',')
    except Exception as e:
        print(f"Error leyendo {file_path}: {e}")
        return None

    # 1. Limpieza de Cabeceras
    # Renombrar columnas comunes eliminando el sufijo '#es'
    df.columns = [col.replace('#es', '').strip() for col in df.columns]
    
    # 2. Filtrado de Granularidad Temporal
    if 'TIME_PERIOD_CODE' in df.columns:
        # Los datos mensuales tienen el formato "YYYY-MXX"
        df = df[df['TIME_PERIOD_CODE'].str.contains('-M', na=False)].copy()
        
        # Extraer Año y Mes
        df['Year'] = df['TIME_PERIOD_CODE'].str.split('-M').str[0].astype(int)
        df['Month'] = df['TIME_PERIOD_CODE'].str.split('-M').str[1].astype(int)
        
        # Crear fecha real para series temporales
        df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2) + '-01')
    
    # 3. Tratamiento de Información Confidencial y Nulos
    if 'OBS_VALUE' in df.columns:
        # Convertir a float. Los strings como '..' (confidencial) o vacíos se vuelven NaN
        df['OBS_VALUE'] = pd.to_numeric(df['OBS_VALUE'], errors='coerce')
        
        # Ordenar por territorio, métrica y fecha para una correcta interpolación
        sort_cols = ['TERRITORIO_CODE', 'Date']
        if 'MEDIDAS_CODE' in df.columns:
            sort_cols.insert(1, 'MEDIDAS_CODE')
        
        df = df.sort_values(by=sort_cols).reset_index(drop=True)
        
        # Imputación: Forward fill (llevar el valor anterior hacia adelante) limitado a 3 meses consecutivos
        # Esto es conservador y mantiene la tendencia sin inventar datos donde hay vacíos largos.
        # Agrupamos por Territorio y Métrica para no mezclar datos
        group_cols = ['TERRITORIO_CODE']
        if 'MEDIDAS_CODE' in df.columns:
            group_cols.append('MEDIDAS_CODE')
            
        df['OBS_VALUE'] = df.groupby(group_cols)['OBS_VALUE'].ffill(limit=3)

    # 4. Normalización Territorial y Categórica
    # Dejamos las columnas de _CODE para agrupaciones futuras en el EDA.
    
    # 5. Gestión de Outliers (Efecto COVID-19)
    # Consideramos pandemia dura desde Marzo 2020 hasta Diciembre 2021 aprox en turismo
    if 'Date' in df.columns:
        df['is_pandemic'] = ((df['Date'] >= '2020-03-01') & (df['Date'] <= '2021-12-31')).astype(int)

    # Seleccionar y ordenar las columnas finales relevantes
    # Priorizamos: Territorio, Fecha, Medida, Valor, Flag Pandemia
    cols_to_keep = [c for c in df.columns if c not in ['NOTAS_OBSERVACION', 'CONFIDENCIALIDAD_OBSERVACION', 'CONFIDENCIALIDAD_OBSERVACION_CODE', 'ESTADO_OBSERVACION', 'ESTADO_OBSERVACION_CODE']]
    
    # Mover Date, Year, Month al principio si existen
    for col in ['is_pandemic', 'Month', 'Year', 'Date']:
        if col in cols_to_keep:
            cols_to_keep.insert(0, cols_to_keep.pop(cols_to_keep.index(col)))
            
    df = df[cols_to_keep]

    return df

def main():
    raw_dir = 'data/raw'
    processed_dir = 'data/processed'
    os.makedirs(processed_dir, exist_ok=True)
    
    files = {
        'hoteles_categorias.csv': 'hoteles_limpio.csv',
        'apartamentos.csv': 'apartamentos_limpio.csv',
        'viviendas_vacacionales.csv': 'viviendas_vacacionales_limpio.csv',
        'establecimientos_3_estrellas.csv': 'estrellas_3_limpio.csv'
    }
    
    for raw_name, clean_name in files.items():
        raw_path = os.path.join(raw_dir, raw_name)
        if os.path.exists(raw_path):
            df_clean = clean_istac_csv(raw_path)
            if df_clean is not None:
                output_path = os.path.join(processed_dir, clean_name)
                df_clean.to_csv(output_path, index=False)
                print(f" -> Guardado con éxito: {output_path} (Filas: {len(df_clean)})")
        else:
            print(f"No se encontró el archivo: {raw_path}")

if __name__ == "__main__":
    main()
