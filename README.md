# 🏝️ Canarias Tourism AI: Sistema de Inteligencia y Predicción de Ocupación Turística

Este proyecto de Inteligencia de Negocio y Machine Learning tiene como objetivo analizar, modelar y predecir la ocupación hotelera y extrahotelera en las Islas Canarias utilizando datos abiertos del **ISTAC** (Instituto Canario de Estadística).

La plataforma cuenta con un microservicio de inferencia en tiempo real (**FastAPI**), una base de datos distribuida en la nube (**MongoDB Atlas**), un pipeline de entrenamiento con validación cruzada temporal y un dashboard interactivo premium (**Streamlit**) con mapas de calor georreferenciados (GeoJSON) y simulador de escenarios económicos.

---

## 🛠️ Arquitectura y Estructura del Proyecto

El sistema está diseñado de manera modular y profesional:

```
├── data/
│   ├── raw/               # Archivos CSV originales descargados de ISTAC
│   └── processed/         # Datasets limpios, imputados y archivos GeoJSON
├── models/                # Modelos serializados (.pkl) y reportes/gráficos científicos
├── notebooks/             # Análisis Exploratorio de Datos (EDA) y Notebook Colab
├── src/                   # Código fuente modular
│   ├── app.py             # Punto de entrada de la interfaz en Streamlit
│   ├── pages_render.py    # Lógica de renderizado y visualizaciones del Dashboard
│   ├── data_loader.py     # Gestor de carga con caché de Streamlit e integración de servicios
│   ├── config.py          # Constantes, estilos CSS personalizados y georreferenciación
│   ├── api.py             # Microservicio de Inferencia de Producción (FastAPI)
│   ├── train_models.py    # Pipeline de entrenamiento y evaluación científica (ROC, Residuos, etc.)
│   ├── mongo_ingest.py    # Ingestión de lotes de datos históricos en MongoDB Atlas
│   └── data_cleaning.py   # Limpieza, curación e imputación de series temporales
├── .env.example           # Plantilla de configuración de variables de entorno
├── requirements.txt       # Dependencias del proyecto python
└── iniciar_dashboard.bat  # Script de arranque en un solo clic para Windows
```

---

## 🚀 Características Clave

### 1. Inferencia Híbrida Inteligente y Tolerancia a Fallos (Offline Fallback)
*   **Base de datos NoSQL**: Si la conexión con **MongoDB Atlas** está activa, los datos históricos se consultan desde la nube; si falla o está desconectado, el dashboard realiza una transición transparente a los CSVs locales en `data/processed/`.
*   **Servicio de Predicción**: El cálculo principal se ejecuta a través de peticiones HTTP POST al microservicio **FastAPI** (puerto `8000`). Si el microservicio está apagado, el dashboard utiliza un fallback local instantáneo cargando el modelo XGBoost mediante `joblib`.
*   **Selectores sin Lag**: La proyección del forecast a 12 meses vista se realiza mediante un bucle en memoria ultra rápido en el cliente, logrando interactividad en tiempo real sin spinners de carga molestos.

### 2. Dashboard de Inteligencia de Negocio Premium
*   **Mapas de Calor Coropléticos**: Mapas interactivos por Isla y por Municipio (más de 30 destinos turísticos) utilizando geometrías GeoJSON reales en 3D sobre mapas oscuros.
*   **Simulador de Escenarios**: Configura vectores de entrada interactivos o aplica escenarios prediseñados de simulación macroeconómica (Reactivación Récord, Crisis Turística, Estabilidad Inercial).
*   **Diagnóstico Científico**: Panel técnico protegido por lazy loading que despliega en pestañas (`st.tabs`) 5 análisis de rendimiento del modelo:
    1. Importancia Relativa de Variables.
    2. Validación Temporal (Predicción vs Real 2025-2026).
    3. Análisis completo de Residuos (histograma, QQ-Plot, sesgos estacionales).
    4. Curva de Aprendizaje (estabilidad del error).
    5. Curvas ROC y Precision-Recall para clasificar temporadas de Alta Ocupación ($\ge70\%$).

### 3. Modelado Científico (XGBoost Champion)
Se evaluaron múltiples algoritmos mediante **TimeSeriesSplit** sobre una partición de prueba (holdout 2025-2026) libre de sesgo temporal:

| Modelo | CV_RMSE (Val) | CV_R² (Val) | MAE (Test) | RMSE (Test) | R² (Test) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **XGBoost (Boosting)** | **4.324** | **0.899** | **1.616** | **2.087** | **0.915** |
| Random Forest | 4.344 | 0.904 | 1.653 | 2.227 | 0.904 |
| Red Neuronal (MLP) | 6.153 | 0.822 | 2.328 | 2.952 | 0.831 |
| Regresión Lineal | 6.853 | 0.778 | 3.570 | 4.367 | 0.629 |

El modelo ganador final fue re-entrenado con el 100% de los datos históricos para su puesta en producción.

---

## 🔧 Requisitos e Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone <tu-repositorio-url>
    cd <directorio-del-proyecto>
    ```

2.  **Instalar dependencias**:
    Se recomienda usar un entorno virtual de Python (venv):
    ```bash
    python -m venv venv
    venv\Scripts\activate       # En Windows
    pip install -r requirements.txt
    ```

3.  **Configurar Variables de Entorno**:
    Crea un archivo llamado `.env` en la raíz del proyecto basándote en el archivo `.env.example`:
    ```ini
    MONGO_URI=mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/?appName=<nombre_app>
    MONGO_DB_NAME=turismo_canarias
    ```

---

## 🏃 Cómo Ejecutar el Proyecto

### Opción A: Arranque Rápido (Recomendado en Windows)
Haz doble clic en el archivo [`iniciar_dashboard.bat`](file:///c:/Users/Manue/Documents/Proyecto%20de%20clase/iniciar_dashboard.bat). Este script automatiza:
1. El arranque en segundo plano del microservicio de FastAPI con Uvicorn (`localhost:8000`).
2. El lanzamiento en tu navegador del dashboard interactivo de Streamlit.

### Opción B: Arranque Manual (Terminales Separadas)

1.  **Iniciar la API de Inferencia (FastAPI)**:
    ```bash
    uvicorn src.api:app --reload --port 8000
    ```
2.  **Iniciar el Dashboard (Streamlit)**:
    ```bash
    streamlit run src/app.py
    ```

### Ingesta de Datos y Reentrenamiento (Opcional)
*   Para cargar datos en tu cluster de MongoDB Atlas: `python src/mongo_ingest.py`
*   Para volver a entrenar los modelos y regenerar las figuras y el informe Markdown: `python src/train_models.py`
