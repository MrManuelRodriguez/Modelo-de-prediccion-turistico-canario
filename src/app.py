import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from config import CATEGORIAS, CSS
from data_loader import load_hoteles, load_apartamentos, load_viviendas, load_model, check_api_health, get_mongo_db
from pages_render import (
    page_analisis, page_comparativa, page_estacionalidad,
    page_viviendas, page_prediccion
)

st.set_page_config(page_title="Canarias Tourism AI", page_icon="🏝️",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

# Carga de datos
df_hot  = load_hoteles()
df_apto = load_apartamentos()
df_viv  = load_viviendas()
model, features_list = load_model()

# Sidebar
with st.sidebar:
    st.title("🏝️ Canarias AI")
    st.markdown("**Plataforma de Inteligencia Turística**")
    
    # Estado de servicios (API y Base de Datos)
    api_ok = check_api_health()
    db_ok = get_mongo_db() is not None
    
    c_api, c_db = st.columns(2)
    with c_api:
        if api_ok:
            st.caption("🟢 API: **ONLINE**")
        else:
            st.caption("🔴 API: **OFFLINE**")
    with c_db:
        if db_ok:
            st.caption("🟢 NoSQL: **ONLINE**")
        else:
            st.caption("🔴 NoSQL: **OFFLINE**")
            
    st.divider()
    page = st.radio("Sección", [
        "📊 Análisis de Mercado",
        "📅 Comparativa Interanual",
        "🔥 Estacionalidad",
        "🏠 Viviendas Vacacionales",
        "🤖 Predicción IA",
    ])
    st.divider()
    cat_sel = st.selectbox("Categoría de Hotel", list(CATEGORIAS.keys()),
                           format_func=lambda x: CATEGORIAS[x])
    st.divider()
    st.caption(f"Mostrando: **{CATEGORIAS[cat_sel]}**")
    st.caption("Fuente: ISTAC — datos abiertos Canarias")

# Invalidar predicción si cambia categoría
if st.session_state.get("pred_cat") != cat_sel:
    for k in ["pred_val", "pred_month", "pred_year", "pred_cat"]:
        st.session_state.pop(k, None)

# Datos filtrados para Canarias (ES70) + categoría
df_can = df_hot[
    (df_hot["TERRITORIO_CODE"] == "ES70") &
    (df_hot["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE"] == cat_sel)
].copy()

# Router de páginas
if   page == "📊 Análisis de Mercado":
    page_analisis(df_hot, df_can, cat_sel)
elif page == "📅 Comparativa Interanual":
    page_comparativa(df_hot, df_can, df_apto, cat_sel)
elif page == "🔥 Estacionalidad":
    page_estacionalidad(df_can, cat_sel)
elif page == "🏠 Viviendas Vacacionales":
    page_viviendas(df_viv)
elif page == "🤖 Predicción IA":
    page_prediccion(df_can, cat_sel, model, features_list)
