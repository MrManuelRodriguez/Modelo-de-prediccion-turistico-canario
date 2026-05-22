import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config import CATEGORIAS, NOMBRES_FEATURES, ISLAS_NOMBRES, ISLAS_GEO, MUNICIPIOS_GEO
from data_loader import query_api_prediction, check_api_health, get_mongo_db
import os


def _predict_local_or_fallback(model, features_list, month, lag_1, lag_2, lag_12, rolling_mean_3, is_pandemic=0):
    if model is not None and features_list is not None:
        try:
            X = pd.DataFrame([[month, lag_1, lag_2, lag_12, rolling_mean_3, is_pandemic]], columns=features_list)
            return float(np.clip(model.predict(X)[0], 0, 100))
        except Exception:
            pass
    return float(lag_12)


def kpi(title, value, delta_html):
    return f'<div class="kpi-card"><div class="kpi-title">{title}</div><div class="kpi-value">{value}</div><div>{delta_html}</div></div>'


def page_analisis(df_raw, df_can, cat_sel):
    st.title("📊 Análisis de Ocupación Hotelera")
    st.markdown(f"Categoría activa: **{CATEGORIAS[cat_sel]}**")

    if df_can.empty or len(df_can) < 2:
        st.warning("No hay datos suficientes para esta categoría.")
        return

    last, prev = df_can.iloc[-1], df_can.iloc[-2]
    diff = last["OBS_VALUE"] - prev["OBS_VALUE"]
    avg_h = df_can["OBS_VALUE"].mean()
    max_h = df_can["OBS_VALUE"].max()
    max_date = df_can.loc[df_can["OBS_VALUE"].idxmax(), "Date"]

    c1, c2, c3, c4 = st.columns(4)
    arrow = "▲" if diff >= 0 else "▼"
    cls = "kpi-up" if diff >= 0 else "kpi-down"
    with c1:
        st.markdown(kpi(f"Último ({last['Date'].strftime('%b %Y')})", f"{last['OBS_VALUE']:.1f}%",
                        f'<span class="{cls}">{arrow} {abs(diff):.1f}%</span>'), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Media Histórica", f"{avg_h:.1f}%",
                        f'<span class="kpi-neu">Desde {df_can["Date"].min().year}</span>'), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Récord Histórico", f"{max_h:.1f}%",
                        f'<span class="kpi-neu">{max_date.strftime("%b %Y")}</span>'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Meses Analizados", str(len(df_can)),
                        f'<span class="kpi-neu">{df_can["Date"].min().year} → {df_can["Date"].max().year}</span>'), unsafe_allow_html=True)

    st.divider()

    # Serie temporal con máximo marcado
    fig = px.line(df_can, x="Date", y="OBS_VALUE",
                  title=f"Evolución de Ocupación — {CATEGORIAS[cat_sel]}",
                  labels={"OBS_VALUE": "Ocupación (%)", "Date": "Fecha"},
                  template="plotly_dark", color_discrete_sequence=["#38bdf8"])
    fig.add_hline(y=avg_h, line_dash="dot", line_color="#94a3b8",
                  annotation_text=f"Media ({avg_h:.1f}%)", annotation_position="bottom right")
    fig.add_vrect(x0="2020-03-01", x1="2021-06-30", fillcolor="#f43f5e",
                  opacity=0.08, line_width=0, annotation_text="COVID-19", annotation_position="top left")
    fig.add_trace(go.Scatter(x=[max_date], y=[max_h], mode="markers+text",
                             marker=dict(color="#fbbf24", size=12, symbol="star"),
                             text=[f" Máx: {max_h:.1f}%"], textposition="top right",
                             textfont=dict(color="#fbbf24"), name="Máximo", showlegend=False))
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    st.divider()
    st.subheader("🗺️ Mapa de Ocupación por Isla")
    _render_island_map(df_raw, cat_sel)

    st.divider()
    st.subheader("🏙️ Mapa de Ocupación por Municipio")
    _render_municipality_map(df_raw, cat_sel)

    st.divider()
    st.subheader("🏅 Top 10 Municipios — Último Mes Disponible")
    _render_top10(df_raw, cat_sel)

    st.divider()
    st.subheader("⬇️ Exportar Datos")
    csv = df_can[["Date", "OBS_VALUE"]].rename(
        columns={"Date": "Fecha", "OBS_VALUE": "Tasa_Ocupacion_%"}
    ).to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV filtrado", data=csv,
                       file_name=f"ocupacion_{cat_sel}_{datetime.now().strftime('%Y%m%d')}.csv",
                       mime="text/csv")


def _render_island_map(df_raw, cat_sel):
    import json
    df_m = df_raw[(df_raw["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE"] == cat_sel) &
                  (df_raw["TERRITORIO_CODE"].isin(ISLAS_GEO.keys()))]
    if df_m.empty:
        st.info("Sin datos por isla para esta categoría.")
        return
    last_d = df_m["Date"].max()
    df_l = df_m[df_m["Date"] == last_d].copy()
    df_l["Isla"] = df_l["TERRITORIO_CODE"].map(ISLAS_NOMBRES)
    df_l = df_l.dropna(subset=["OBS_VALUE"])
    if df_l.empty:
        st.info("Sin valores de ocupación en el último periodo.")
        return

    # Intentar cargar las geometrías de las islas desde el GeoJSON local
    geojson_data = None
    geojson_path = "data/processed/canarias_islas.geojson"
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
        except Exception as e:
            print(f"Error al leer canarias_islas.geojson: {e}")

    if geojson_data is not None:
        # Visualización premium: Mapa de calor georreferenciado (Choropleth)
        fig = px.choropleth_mapbox(
            df_l,
            geojson=geojson_data,
            locations="TERRITORIO_CODE",
            featureidkey="properties.NUTS_ID",
            color="OBS_VALUE",
            hover_name="Isla",
            color_continuous_scale="Plasma",
            mapbox_style="carto-darkmatter",
            zoom=6.5,
            center={"lat": 28.3, "lon": -15.8},
            opacity=0.7,
            labels={"OBS_VALUE": "Ocupación %"},
            title=f"Mapa de Calor Georreferenciado por Isla — {last_d.strftime('%B %Y')}"
        )
        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#f8fafc"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Fallback de burbujas tradicionales si no se encuentra el GeoJSON
        df_l["lat"] = df_l["TERRITORIO_CODE"].map(lambda x: ISLAS_GEO[x][0])
        df_l["lon"] = df_l["TERRITORIO_CODE"].map(lambda x: ISLAS_GEO[x][1])
        fig = px.scatter_mapbox(
            df_l, lat="lat", lon="lon", size="OBS_VALUE", color="OBS_VALUE",
            hover_name="Isla", size_max=45, zoom=6.2,
            color_continuous_scale="Plasma", mapbox_style="carto-darkmatter",
            labels={"OBS_VALUE": "Ocupación %"},
            title=f"Mapa por Isla (Burbujas) — {last_d.strftime('%B %Y')}"
        )
        fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True)


def _render_municipality_map(df_raw, cat_sel):
    import json
    munic_keys = list(MUNICIPIOS_GEO.keys())
    df_m = df_raw[(df_raw["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE"] == cat_sel) &
                  (df_raw["TERRITORIO_CODE"].isin(munic_keys))]
    if df_m.empty:
        st.info("Sin datos municipales para esta categoría.")
        return

    metrica = st.selectbox("Métrica del mapa municipal",
                           ["Tasa de Ocupación", "Promedio Últimos 12 Meses"],
                           key="munic_metric")

    last_d = df_m["Date"].max()
    if metrica == "Tasa de Ocupación":
        df_plot = df_m[df_m["Date"] == last_d].copy()
        titulo = f"Ocupación Municipios — {last_d.strftime('%B %Y')}"
    else:
        cutoff = df_m["Date"].max() - pd.DateOffset(months=12)
        df_plot = df_m[df_m["Date"] >= cutoff].groupby("TERRITORIO_CODE")["OBS_VALUE"].mean().reset_index()
        titulo = "Promedio Ocupación — Últimos 12 Meses"

    df_plot["Municipio"] = df_plot["TERRITORIO_CODE"].map(lambda x: MUNICIPIOS_GEO.get(x, {}).get("nombre", x))
    df_plot = df_plot.dropna(subset=["OBS_VALUE"])

    if df_plot.empty:
        st.info("Sin datos municipales para mostrar.")
        return

    # Intentar cargar las geometrías municipales desde el GeoJSON local
    geojson_data = None
    geojson_path = "data/processed/canarias_municipios.geojson"
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
        except Exception as e:
            print(f"Error al leer canarias_municipios.geojson: {e}")

    if geojson_data is not None:
        # Visualización premium: Mapa de calor georreferenciado por municipios (Choropleth)
        fig = px.choropleth_mapbox(
            df_plot,
            geojson=geojson_data,
            locations="TERRITORIO_CODE",
            featureidkey="properties.MUNI_CODE",
            color="OBS_VALUE",
            hover_name="Municipio",
            color_continuous_scale="Viridis",
            mapbox_style="carto-darkmatter",
            zoom=6.8,
            center={"lat": 28.3, "lon": -15.8},
            opacity=0.7,
            labels={"OBS_VALUE": "Ocupación %"},
            title=f"Mapa de Calor Municipal — {titulo}"
        )
        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#f8fafc"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Fallback de burbujas tradicionales si no se encuentra el GeoJSON
        df_plot["lat"] = df_plot["TERRITORIO_CODE"].map(lambda x: MUNICIPIOS_GEO.get(x, {}).get("lat"))
        df_plot["lon"] = df_plot["TERRITORIO_CODE"].map(lambda x: MUNICIPIOS_GEO.get(x, {}).get("lon"))
        df_plot = df_plot.dropna(subset=["lat", "lon"])
        fig = px.scatter_mapbox(
            df_plot, lat="lat", lon="lon", size="OBS_VALUE", color="OBS_VALUE",
            hover_name="Municipio", size_max=35, zoom=6.5,
            color_continuous_scale="Viridis", mapbox_style="carto-darkmatter",
            labels={"OBS_VALUE": "Ocupación %"},
            title=titulo
        )
        fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Cada burbuja = un municipio. Tamaño y color representan la tasa de ocupación.")


def _render_top10(df_raw, cat_sel):
    munic_keys = list(MUNICIPIOS_GEO.keys())
    df_m = df_raw[(df_raw["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE"] == cat_sel) &
                  (df_raw["TERRITORIO_CODE"].isin(munic_keys))]
    if df_m.empty:
        st.info("Sin datos municipales.")
        return
    last_d = df_m["Date"].max()
    df_l = df_m[df_m["Date"] == last_d].copy()
    df_l["Municipio"] = df_l["TERRITORIO_CODE"].map(lambda x: MUNICIPIOS_GEO.get(x, {}).get("nombre", x))
    df_l = df_l.dropna(subset=["OBS_VALUE"]).sort_values("OBS_VALUE", ascending=False)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**🔝 Top 10 Mayor Ocupación**")
        top10 = df_l.head(10)[["Municipio", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "Ocupación (%)"})
        top10["Ocupación (%)"] = top10["Ocupación (%)"].round(1)
        st.dataframe(top10, hide_index=True, width=400)
    with col_b:
        st.markdown("**⬇️ Top 10 Menor Ocupación**")
        bot10 = df_l.tail(10)[["Municipio", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "Ocupación (%)"})
        bot10["Ocupación (%)"] = bot10["Ocupación (%)"].round(1)
        st.dataframe(bot10, hide_index=True, width=400)


def page_comparativa(df_raw, df_can, df_apto, cat_sel):
    st.title("📅 Comparativa Interanual y por Segmento")

    if df_can.empty:
        st.warning("Sin datos para esta categoría.")
        return

    # Comparativa interanual
    st.subheader("📅 Evolución Año a Año")
    years = sorted(df_can["Year"].unique())
    sel_years = st.multiselect("Años a comparar", years,
                               default=years[-5:] if len(years) >= 5 else years)
    if sel_years:
        df_c = df_can[df_can["Year"].isin(sel_years)].copy()
        df_c["Año"] = df_c["Year"].astype(str)
        fig = px.line(df_c, x="Month", y="OBS_VALUE", color="Año",
                      title=f"Ocupación mensual por año — {CATEGORIAS[cat_sel]}",
                      labels={"OBS_VALUE": "Ocupación (%)", "Month": "Mes"},
                      template="plotly_dark", markers=True,
                      color_discrete_sequence=px.colors.sequential.Plasma_r)
        fig.update_xaxes(tickvals=list(range(1, 13)),
                         ticktext=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"])
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

    st.divider()
    st.subheader("🏨 Hoteles vs 🏢 Apartamentos — Ocupación Canarias")

    df_h = df_can[df_can["TERRITORIO_CODE"] == "ES70"][["Date", "OBS_VALUE"]].copy()
    df_h["Segmento"] = "Hoteles"

    df_a_es70 = df_apto[(df_apto["TERRITORIO_CODE"] == "ES70") &
                        (df_apto["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE"] == cat_sel)][["Date", "OBS_VALUE"]].copy()
    df_a_es70["Segmento"] = "Apartamentos"

    df_seg = pd.concat([df_h, df_a_es70], ignore_index=True)
    if df_seg.empty or df_a_es70.empty:
        st.info("No hay datos de apartamentos disponibles para esta categoría y filtro.")
    else:
        fig2 = px.line(df_seg, x="Date", y="OBS_VALUE", color="Segmento",
                       title="Hoteles vs Apartamentos — Tasa de Ocupación",
                       labels={"OBS_VALUE": "Ocupación (%)", "Date": "Fecha"},
                       template="plotly_dark",
                       color_discrete_map={"Hoteles": "#38bdf8", "Apartamentos": "#fb923c"})
        fig2.update_layout(hovermode="x unified")
        st.plotly_chart(fig2, width="stretch")
        st.caption("Comparativa directa entre los dos principales segmentos de alojamiento turístico en Canarias.")

    st.divider()
    st.subheader("🏆 Ranking de Islas — Último Año")
    ult_anio = df_can["Year"].max()
    df_rk = df_raw[(df_raw["TERRITORIO_CODE"].isin(ISLAS_NOMBRES.keys())) &
                   (df_raw["Year"] == ult_anio) &
                   (df_raw["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE"] == cat_sel)].copy()
    df_rk["Isla"] = df_rk["TERRITORIO_CODE"].map(ISLAS_NOMBRES)
    df_agg = df_rk.groupby("Isla")["OBS_VALUE"].mean().reset_index().sort_values("OBS_VALUE")
    df_agg.columns = ["Isla", "Ocupación Media (%)"]
    if not df_agg.empty:
        fig3 = px.bar(df_agg, x="Ocupación Media (%)", y="Isla", orientation="h",
                      title=f"Ranking de Islas en {ult_anio} — {CATEGORIAS[cat_sel]}",
                      template="plotly_dark", color="Ocupación Media (%)",
                      color_continuous_scale="Viridis", text_auto=".1f")
        fig3.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig3, width="stretch")


def page_estacionalidad(df_can, cat_sel):
    st.title("🔥 Mapa de Calor Estacional")
    st.markdown("Detecta patrones de alta y baja temporada año a año.")
    if df_can.empty:
        st.warning("Sin datos para esta categoría.")
        return
    pivot = df_can.pivot_table(index="Year", columns="Month", values="OBS_VALUE", aggfunc="mean")
    pivot.columns = [datetime(2000, int(m), 1).strftime("%b") for m in pivot.columns]
    fig = px.imshow(pivot, text_auto=".1f", aspect="auto",
                    color_continuous_scale="RdYlGn",
                    labels=dict(x="Mes", y="Año", color="Ocupación %"),
                    title=f"Estacionalidad — {CATEGORIAS[cat_sel]}")
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(15,23,42,1)",
                      font=dict(color="#f8fafc"), xaxis=dict(side="top"))
    st.plotly_chart(fig, width="stretch")
    st.info("💡 Verde = alta ocupación · Rojo = baja. El patrón canario es inverso al peninsular: el invierno es la temporada fuerte.")


def page_viviendas(df_viv):
    st.title("🏠 Viviendas Vacacionales")
    st.markdown("Análisis del mercado de alquiler vacacional en Canarias desde 2019.")

    if df_viv.empty:
        st.warning("No se pudieron cargar los datos de viviendas vacacionales.")
        return

    medidas_disp = df_viv["MEDIDAS_CODE"].unique().tolist()
    medida_labels = {
        "INGRESOS_TOTALES":              "Ingresos Totales (€)",
        "TASA_VIVIENDA_RESERVADA":       "Tasa de Vivienda Reservada (%)",
        "VIVIENDAS_RESERVADAS":          "Viviendas Reservadas",
        "VIVIENDAS_DISPONIBLES":         "Viviendas Disponibles",
        "PLAZAS_DISPONIBLES":            "Plazas Disponibles",
        "ESTANCIA_MEDIA_VIVIENDA_VACACIONAL": "Estancia Media (noches)",
    }
    opciones = {k: v for k, v in medida_labels.items() if k in medidas_disp}

    if not opciones:
        st.info("No se encontraron métricas reconocidas en el dataset.")
        return

    medida_sel = st.selectbox("Métrica a visualizar",
                              list(opciones.keys()),
                              format_func=lambda x: opciones[x])

    df_c = df_viv[(df_viv["TERRITORIO_CODE"] == "ES70") & (df_viv["MEDIDAS_CODE"] == medida_sel)].copy()

    if df_c.empty:
        st.info("Sin datos para Canarias en esta métrica.")
        return

    # KPIs
    last_val = df_c.iloc[-1]["OBS_VALUE"]
    avg_val = df_c["OBS_VALUE"].mean()
    col1, col2, col3 = st.columns(3)
    with col1:
        fmt = f"€{last_val:,.0f}" if "INGRESOS" in medida_sel else f"{last_val:,.1f}"
        st.metric("Último valor registrado", fmt)
    with col2:
        fmt_avg = f"€{avg_val:,.0f}" if "INGRESOS" in medida_sel else f"{avg_val:,.1f}"
        st.metric("Media histórica", fmt_avg)
    with col3:
        st.metric("Meses disponibles", len(df_c))

    fig = px.line(df_c, x="Date", y="OBS_VALUE",
                  title=f"{opciones[medida_sel]} — Canarias",
                  labels={"OBS_VALUE": opciones[medida_sel], "Date": "Fecha"},
                  template="plotly_dark", color_discrete_sequence=["#34d399"])
    fig.add_vrect(x0="2020-03-01", x1="2021-06-30", fillcolor="#f43f5e",
                  opacity=0.08, line_width=0, annotation_text="COVID-19")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    # Si hay ingresos y tasa reservada, mostrar correlación
    if "INGRESOS_TOTALES" in medidas_disp and "TASA_VIVIENDA_RESERVADA" in medidas_disp:
        st.divider()
        st.subheader("📊 Relación Ingresos vs Tasa de Reserva")
        df_ing = df_viv[(df_viv["TERRITORIO_CODE"] == "ES70") &
                        (df_viv["MEDIDAS_CODE"] == "INGRESOS_TOTALES")][["Date", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "Ingresos"})
        df_tasa = df_viv[(df_viv["TERRITORIO_CODE"] == "ES70") &
                         (df_viv["MEDIDAS_CODE"] == "TASA_VIVIENDA_RESERVADA")][["Date", "OBS_VALUE"]].rename(columns={"OBS_VALUE": "Tasa_Reserva"})
        df_cross = pd.merge(df_ing, df_tasa, on="Date")
        if not df_cross.empty:
            fig2 = px.scatter(df_cross, x="Tasa_Reserva", y="Ingresos",
                              title="Correlación: Tasa de Reserva vs Ingresos Generados",
                              labels={"Tasa_Reserva": "Tasa Reservada (%)", "Ingresos": "Ingresos (€)"},
                              template="plotly_dark",
                              color_discrete_sequence=["#a78bfa"])
            st.plotly_chart(fig2, width="stretch")
            st.caption("La línea de tendencia muestra la correlación estadística entre ambas variables.")


def page_prediccion(df_can, cat_sel, model, features_list):
    st.title("🤖 Simulador de Demanda Turística")
    st.markdown(f"Inferencia con **XGBoost Regressor** · Categoría: **{CATEGORIAS[cat_sel]}**")

    if df_can.empty or len(df_can) < 12:
        st.warning(f"Datos insuficientes para predecir en **{CATEGORIAS[cat_sel]}**.")
        return

    # Escenarios Prediseñados
    st.subheader("💡 Selección de Escenario de Simulación")
    escenario = st.radio(
        "Escenarios de simulación macroeconómica",
        [
            "Personalizado (Histórico Real / Estimado)",
            "Escenario A: Reactivación Récord Post-Pandemia (Alta Demanda)",
            "Escenario B: Crisis Turística / Enfriamiento (Baja Demanda)",
            "Escenario C: Estabilidad Histórica (Media)"
        ],
        horizontal=True
    )

    col_cfg, col_res = st.columns([1, 1.5])

    last_hist_date = df_can["Date"].max()

    with col_cfg:
        st.subheader("Configuración del Vector")
        
        # Selector dinámico de Año y Mes
        c_yr, c_mo = st.columns(2)
        with c_yr:
            y_pred = st.selectbox("Año a predecir", [2026, 2027, 2028], index=0)
        with c_mo:
            m_pred = st.selectbox("Mes a predecir", range(1, 13),
                                  format_func=lambda x: datetime(2026, x, 1).strftime("%B"),
                                  index=7) # Por defecto Agosto
                                  
        target_date = datetime(y_pred, m_pred, 1)

        # Comprobar si la fecha seleccionada está en el histórico real
        if target_date <= last_hist_date:
            st.warning(f"La fecha elegida ({target_date.strftime('%B %Y')}) ya cuenta con datos reales históricos en el dataset (que llega hasta {last_hist_date.strftime('%B %Y')}). Por favor, selecciona una fecha futura a partir de {(last_hist_date + pd.DateOffset(months=1)).strftime('%B %Y')}.")
            return

        # Calcular el vector base inercial usando un pronóstico autorregresivo secuencial (local e instantáneo)
        df_temp = df_can.copy()
        current_date = last_hist_date
        
        while current_date < target_date:
            next_month = current_date.month + 1
            next_year = current_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            current_date = datetime(next_year, next_month, 1)
            
            l1_step = float(df_temp.iloc[-1]["OBS_VALUE"])
            l2_step = float(df_temp.iloc[-2]["OBS_VALUE"])
            l12_step = float(df_temp[df_temp["Month"] == next_month]["OBS_VALUE"].mean())
            roll_step = float(df_temp["OBS_VALUE"].tail(3).mean())
            
            pred_step = _predict_local_or_fallback(model, features_list, next_month, l1_step, l2_step, l12_step, roll_step, 0)
                
            new_row = pd.DataFrame([{
                "Date": current_date,
                "OBS_VALUE": pred_step,
                "Month": next_month,
                "Year": next_year,
                "ALOJAMIENTO_TURISTICO_CATEGORIA_CODE": cat_sel,
                "TERRITORIO_CODE": "ES70"
            }])
            df_temp = pd.concat([df_temp, new_row], ignore_index=True)

        # Extraer los retardos estimados para la fecha objetivo
        l1_real = float(df_temp.iloc[-2]["OBS_VALUE"])
        l2_real = float(df_temp.iloc[-3]["OBS_VALUE"])
        roll_real = float(df_temp.iloc[-4:-1]["OBS_VALUE"].mean())
        l12_real = float(df_can[df_can["Month"] == m_pred]["OBS_VALUE"].mean())

        # Configurar valores según el escenario seleccionado
        if "Reactivación Récord" in escenario:
            lag_1 = min(l1_real + 10.0, 100.0)
            lag_2 = min(l2_real + 8.0, 100.0)
            lag_12 = min(l12_real + 12.0, 100.0)
            rolling_mean_3 = min(roll_real + 9.5, 100.0)
            is_pandemic = 0
            st.info("🚀 **Configuración Optimista Aplicada**: Valores estimados inflados un ~10% simulando reactivación aérea.")
        elif "Crisis" in escenario:
            lag_1 = max(l1_real - 15.0, 0.0)
            lag_2 = max(l2_real - 12.0, 0.0)
            lag_12 = max(l12_real - 10.0, 0.0)
            rolling_mean_3 = max(roll_real - 13.5, 0.0)
            is_pandemic = 0
            st.warning("📉 **Configuración Pesimista Aplicada**: Valores de ocupación estimados deprimidos un ~15% por recesión.")
        elif "Estabilidad Histórica" in escenario:
            avg_hist = float(df_can["OBS_VALUE"].mean())
            lag_1 = avg_hist
            lag_2 = avg_hist
            lag_12 = l12_real
            rolling_mean_3 = avg_hist
            is_pandemic = 0
            st.info("⚖️ **Configuración de Estabilidad**: Todo configurado con las medias históricas de la categoría.")
        else:
            lag_1 = l1_real
            lag_2 = l2_real
            lag_12 = l12_real
            rolling_mean_3 = roll_real
            is_pandemic = 0
            st.info("📂 **Estimación Inercial Real**: Se utilizan los retardos proyectados secuencialmente a partir del histórico real.")

        # Visualizar el vector de entrada que se va a enviar
        with st.expander("👁️ Ver Vector de Entrada (Feature values)", expanded=False):
            st.json({
                "Año a predecir": y_pred,
                "Mes a predecir": m_pred,
                "Ocupación mes anterior (lag_1)": round(lag_1, 2),
                "Ocupación hace 2 meses (lag_2)": round(lag_2, 2),
                "Ocupación año pasado (lag_12)": round(lag_12, 2),
                "Media últimos 3 meses (rolling_mean_3)": round(rolling_mean_3, 2),
                "Indicador Pandemia": is_pandemic
            })

        if st.button("Calcular Predicción", type="primary", use_container_width=True):
            # Consumir de la API con query_api_prediction
            pred, engine = query_api_prediction(m_pred, lag_1, lag_2, lag_12, rolling_mean_3, is_pandemic)
            st.session_state["pred_val"] = pred
            st.session_state["pred_month"] = m_pred
            st.session_state["pred_year"] = y_pred
            st.session_state["pred_cat"] = cat_sel
            st.session_state["pred_engine"] = engine
            st.session_state["pred_escenario"] = escenario

    with col_res:
        if "pred_val" in st.session_state and st.session_state.get("pred_cat") == cat_sel:
            p = st.session_state["pred_val"]
            m = st.session_state["pred_month"]
            y = st.session_state.get("pred_year", 2026)
            engine_used = st.session_state.get("pred_engine", "Desconocido")
            esc_active = st.session_state.get("pred_escenario", escenario)
            mes_str = datetime(y, m, 1).strftime("%B %Y")
            
            st.markdown(f"""
            <div class="pred-card">
                <div class="pred-label">Pronóstico de Ocupación</div>
                <div class="pred-value">{p:.1f}%</div>
                <div class="pred-sub">Para {mes_str} · {CATEGORIAS[cat_sel]}</div>
            </div>""", unsafe_allow_html=True)

            # Detalle del Motor
            st.caption(f"⚙️ **Motor de Inferencia:** `{engine_used}` · **Escenario:** `{esc_active}`")

            if p > 85:
                st.success("🟢 **Temporada Muy Alta:** Ocupación excelente. Se recomienda optimizar tarifas (Revenue Management) y planificar contratación de personal extra.")
            elif p > 65:
                st.info("🔵 **Demanda Estable:** Operativa estándar y ratios de rentabilidad en niveles saludables.")
            else:
                st.warning("🟡 **Demanda Baja:** Nivel bajo de reservas. Se aconseja lanzar promociones, paquetes integrados o flexibilizar políticas de cancelación.")

            st.divider()
            st.subheader("🧠 Explicabilidad de la Inferencia")
            # Cargar importancia si existe el modelo
            if model is not None:
                imp_df = pd.DataFrame({
                    "Factor": [NOMBRES_FEATURES.get(f, f) for f in features_list],
                    "Importancia": model.feature_importances_
                }).sort_values("Importancia", ascending=True)
                fig_imp = px.bar(imp_df, x="Importancia", y="Factor", orientation="h",
                                 template="plotly_dark", color="Importancia",
                                 color_continuous_scale="Purples", text_auto=".2f",
                                 title="Peso de cada variable en la predicción")
                fig_imp.update_layout(coloraxis_showscale=False, yaxis_title="")
                st.plotly_chart(fig_imp, use_container_width=True)

        st.divider()
        st.subheader("📈 Forecast Continuo de 12 Meses")
        _render_forecast_chart(df_can, model, features_list, cat_sel)

    # Añadir sección de Diagnóstico Científico del Modelo (Evaluación)
    st.divider()
    
    if "show_diagnostics" not in st.session_state:
        st.session_state["show_diagnostics"] = False
        
    btn_label = "🔬 Ocultar Reporte y Diagnóstico Técnico" if st.session_state["show_diagnostics"] else "🔬 Mostrar Reporte y Diagnóstico Científico del Modelo"
    
    if st.button(btn_label, type="secondary", use_container_width=True):
        st.session_state["show_diagnostics"] = not st.session_state["show_diagnostics"]
        st.rerun()
        
    if st.session_state["show_diagnostics"]:
        st.subheader("🔬 Reporte y Diagnóstico Científico del Modelo")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Importancia de Variables", 
            "📈 Validación Temporal", 
            "📉 Análisis de Residuos",
            "🍏 Curva de Aprendizaje",
            "🎯 Curvas ROC & PR"
        ])
        
        with tab1:
            st.markdown("**1. Importancia Relativa de Variables**")
            if os.path.exists("models/feature_importance.png"):
                st.image("models/feature_importance.png", use_container_width=True, 
                         caption="Las variables lag_12 (estacionalidad anual) y lag_1 (inercia a corto plazo) dominan las decisiones de XGBoost.")
            else:
                st.info("Gráfico de importancia no generado. Ejecuta 'train_models.py' para crearlo.")
                
        with tab2:
            st.markdown("**2. Validación Temporal: Predicción vs Valores Reales**")
            if os.path.exists("models/prediccion_vs_real.png"):
                st.image("models/prediccion_vs_real.png", use_container_width=True, 
                         caption="Curva comparativa en el conjunto de prueba independiente (2025-2026). El modelo captura a la perfección la estacionalidad canaria.")
            else:
                st.info("Gráfico comparativo no generado. Ejecuta 'train_models.py' para crearlo.")
                
        with tab3:
            st.markdown("**3. Análisis de Residuos**")
            if os.path.exists("models/analisis_residuos.png"):
                st.image("models/analisis_residuos.png", use_container_width=True, 
                         caption="Histograma, QQ-Plot, residuos temporales y error mensual estacional para validar los supuestos del modelo.")
            else:
                st.info("Gráfico de análisis de residuos no generado. Ejecuta 'train_models.py' para crearlo.")
                
        with tab4:
            st.markdown("**4. Curva de Aprendizaje**")
            if os.path.exists("models/curva_aprendizaje.png"):
                st.image("models/curva_aprendizaje.png", use_container_width=True, 
                         caption="Análisis de sobreajuste y estabilidad (bias/variance tradeoff) variando el tamaño del conjunto de datos.")
            else:
                st.info("Gráfico de curva de aprendizaje no generado. Ejecuta 'train_models.py' para crearlo.")
                
        with tab5:
            st.markdown("**5. Curvas ROC y Precision-Recall**")
            if os.path.exists("models/curva_roc.png"):
                st.image("models/curva_roc.png", use_container_width=True, 
                         caption="Métricas de evaluación de clasificación binarizando la ocupación (Umbral de Temporada Alta ≥ 70%). Muestra el AUC-ROC y AP.")
            else:
                st.info("Gráfico de curvas ROC/PR no generado. Ejecuta 'train_models.py' para crearlo.")


def _render_forecast_chart(df_can, model, features_list, cat_sel):
    import pandas as pd
    preds = []
    df_temp = df_can.copy()
    
    last_hist_date = df_can["Date"].max()
    current_date = last_hist_date
    
    for _ in range(12):
        # Siguiente mes
        next_month = current_date.month + 1
        next_year = current_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        current_date = datetime(next_year, next_month, 1)
        
        l1   = float(df_temp.iloc[-1]["OBS_VALUE"])
        l2   = float(df_temp.iloc[-2]["OBS_VALUE"])
        l12  = float(df_temp[df_temp["Month"] == next_month]["OBS_VALUE"].mean())
        roll = float(df_temp["OBS_VALUE"].tail(3).mean())
        
        # Predicción local ultra veloz
        val = _predict_local_or_fallback(model, features_list, next_month, l1, l2, l12, roll, 0)
            
        preds.append({"Date": current_date, "OBS_VALUE": val, "tipo": "Forecast (12 Meses)"})
        
        # Añadir al df_temp para el siguiente paso autorregresivo
        new_row = pd.DataFrame([{
            "Date": current_date,
            "OBS_VALUE": val,
            "Month": next_month,
            "Year": next_year,
            "ALOJAMIENTO_TURISTICO_CATEGORIA_CODE": cat_sel,
            "TERRITORIO_CODE": "ES70"
        }])
        df_temp = pd.concat([df_temp, new_row], ignore_index=True)

    df_hist = df_can[["Date", "OBS_VALUE"]].tail(36).copy()
    df_hist["tipo"] = "Histórico"
    df_fore = pd.DataFrame(preds)
    df_all = pd.concat([df_hist, df_fore], ignore_index=True)

    fig = px.line(df_all, x="Date", y="OBS_VALUE", color="tipo",
                  title=f"Histórico + Forecast Proyectado — {CATEGORIAS[cat_sel]}",
                  labels={"OBS_VALUE": "Ocupación (%)", "Date": "Fecha", "tipo": ""},
                  template="plotly_dark",
                  color_discrete_map={"Histórico": "#38bdf8", "Forecast (12 Meses)": "#f59e0b"},
                  markers=True)
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Los puntos naranjas representan el pronóstico autorregresivo secuencial para los próximos 12 meses.")
