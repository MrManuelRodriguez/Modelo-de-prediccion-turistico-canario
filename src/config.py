# config.py - Constantes, coordenadas y estilos

CATEGORIAS = {
    "_T":          "Total General",
    "ESTRELLAS_5": "Lujo (5★)",
    "ESTRELLAS_4": "Superior (4★)",
    "ESTRELLAS_3": "Estándar (3★)",
    "ESTRELLAS_2": "Económico (2★)",
    "ESTRELLAS_1": "Básico (1★)",
}

NOMBRES_FEATURES = {
    "Month":          "Mes del año",
    "lag_1":          "Ocupación mes anterior",
    "lag_2":          "Ocupación hace 2 meses",
    "lag_12":         "Mismo mes del año pasado",
    "rolling_mean_3": "Tendencia últimos 3 meses",
    "is_pandemic":    "Indicador Pandemia",
}

ISLAS_NOMBRES = {
    "ES703": "El Hierro",     "ES704": "Fuerteventura",
    "ES705": "Gran Canaria",  "ES706": "La Gomera",
    "ES707": "La Palma",      "ES708": "Lanzarote",
    "ES709": "Tenerife",
}

ISLAS_GEO = {
    "ES703": [27.733, -18.017], "ES704": [28.359, -14.054],
    "ES705": [27.920, -15.547], "ES706": [28.117, -17.224],
    "ES707": [28.684, -17.765], "ES708": [29.047, -13.590],
    "ES709": [28.292, -16.629],
}

# Coordenadas de municipios turísticos
MUNICIPIOS_GEO = {
    "35003": {"nombre": "Antigua",                    "lat": 28.428, "lon": -13.955},
    "35004": {"nombre": "Arrecife",                   "lat": 28.964, "lon": -13.548},
    "35012": {"nombre": "Mogán",                      "lat": 27.883, "lon": -15.717},
    "35014": {"nombre": "La Oliva",                   "lat": 28.618, "lon": -13.869},
    "35015": {"nombre": "Pájara",                     "lat": 28.333, "lon": -14.150},
    "35016": {"nombre": "Las Palmas de Gran Canaria", "lat": 28.125, "lon": -15.430},
    "35017": {"nombre": "Puerto del Rosario",         "lat": 28.500, "lon": -13.867},
    "35019": {"nombre": "San Bartolomé de Tirajana",  "lat": 27.917, "lon": -15.567},
    "35024": {"nombre": "Teguise",                    "lat": 29.061, "lon": -13.560},
    "35028": {"nombre": "Tías",                       "lat": 28.958, "lon": -13.653},
    "35030": {"nombre": "Tuineje",                    "lat": 28.317, "lon": -14.050},
    "35034": {"nombre": "Yaiza",                      "lat": 28.950, "lon": -13.767},
    "38001": {"nombre": "Adeje",                      "lat": 28.123, "lon": -16.726},
    "38006": {"nombre": "Arona",                      "lat": 28.100, "lon": -16.682},
    "38009": {"nombre": "Breña Baja",                 "lat": 28.633, "lon": -17.767},
    "38013_2007": {"nombre": "Frontera",              "lat": 27.767, "lon": -18.017},
    "38014": {"nombre": "Fuencaliente",               "lat": 28.483, "lon": -17.833},
    "38017": {"nombre": "Granadilla de Abona",        "lat": 28.117, "lon": -16.583},
    "38019": {"nombre": "Güía de Isora",              "lat": 28.200, "lon": -16.783},
    "38023": {"nombre": "San Cristóbal de La Laguna", "lat": 28.487, "lon": -16.316},
    "38024": {"nombre": "Los Llanos de Aridane",      "lat": 28.658, "lon": -17.917},
    "38028": {"nombre": "Puerto de la Cruz",          "lat": 28.414, "lon": -16.549},
    "38035": {"nombre": "San Miguel de Abona",        "lat": 28.050, "lon": -16.617},
    "38036": {"nombre": "San Sebastián de La Gomera", "lat": 28.092, "lon": -17.108},
    "38037": {"nombre": "Santa Cruz de La Palma",     "lat": 28.683, "lon": -17.767},
    "38038": {"nombre": "Santa Cruz de Tenerife",     "lat": 28.464, "lon": -16.252},
    "38040": {"nombre": "Santiago del Teide",         "lat": 28.283, "lon": -16.817},
    "38048": {"nombre": "Valverde",                   "lat": 27.817, "lon": -17.917},
    "38049": {"nombre": "Valle Gran Rey",             "lat": 28.067, "lon": -17.317},
    "38050": {"nombre": "Vallehermoso",               "lat": 28.167, "lon": -17.267},
}

CSS = """
<style>
    [data-testid="stSidebar"] { background-color: #0f172a; }
    .kpi-card {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 14px; padding: 20px 16px;
        border: 1px solid rgba(148,163,184,0.15);
        text-align: center; margin-bottom: 8px;
    }
    .kpi-title { font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; }
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #f8fafc; margin: 6px 0; }
    .kpi-up   { color: #10b981; font-size: 0.88rem; font-weight: 600; }
    .kpi-down { color: #f43f5e; font-size: 0.88rem; font-weight: 600; }
    .kpi-neu  { color: #94a3b8; font-size: 0.88rem; }
    .pred-card {
        background: linear-gradient(135deg,#0f172a,#1e1b4b);
        border-radius: 18px; padding: 35px 25px;
        text-align: center; border: 1px solid #4338ca;
        box-shadow: 0 12px 30px rgba(67,56,202,0.35); margin-bottom: 20px;
    }
    .pred-label { font-size: 0.82rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .pred-value {
        font-size: 4.5rem; font-weight: 900;
        background: -webkit-linear-gradient(#60a5fa,#c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 10px 0;
    }
    .pred-sub { font-size: 1rem; color: #cbd5e1; }
</style>
"""
