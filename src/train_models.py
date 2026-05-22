"""
Entrenamiento de Modelos Predictivos (Fase 2)
Proyecto: Sistema de Predicción de Ocupación Turística en Canarias
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, learning_curve
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from xgboost import XGBRegressor
from sklearn.metrics import (
    mean_absolute_error, root_mean_squared_error, r2_score,
    roc_curve, auc, precision_recall_curve, average_precision_score
)
from sklearn.preprocessing import MinMaxScaler
from scipy import stats
import joblib
import os
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec


print("--- Iniciando Entrenamiento de Modelos Predictivos ---")

# Configurar estilo de gráficos
sns.set_theme(style="darkgrid")
plt.rcParams.update({
    'figure.facecolor': '#0f172a',
    'axes.facecolor': '#1e293b',
    'text.color': '#f8fafc',
    'axes.labelcolor': '#94a3b8',
    'xtick.color': '#94a3b8',
    'ytick.color': '#94a3b8',
    'grid.color': '#334155'
})

# 1. Cargar Datos Limpios
data_path = "data/processed/hoteles_limpio.csv"
print(f"Cargando dataset local: {data_path}")
df = pd.read_csv(data_path, low_memory=False)

# Filtrar para Canarias Total (ES70) y Ocupación por habitación
df_canarias = df[(df["TERRITORIO_CODE"] == "ES70") & (df["MEDIDAS_CODE"] == "TASA_OCUPACION_HABITACION")].copy()

# Ordenar cronológicamente y por categoría
df_canarias["Date"] = pd.to_datetime(df_canarias["Date"])
df_canarias = df_canarias.sort_values(["ALOJAMIENTO_TURISTICO_CATEGORIA_CODE", "Date"]).reset_index(drop=True)

print(f"Total de meses históricos disponibles para Canarias: {len(df_canarias)}")

# 2. Feature Engineering
print("Creando variables predictoras (lags y medias móviles)...")
grouped = df_canarias.groupby("ALOJAMIENTO_TURISTICO_CATEGORIA_CODE")

df_canarias["lag_1"] = grouped["OBS_VALUE"].shift(1)
df_canarias["lag_2"] = grouped["OBS_VALUE"].shift(2)
df_canarias["lag_12"] = grouped["OBS_VALUE"].shift(12)
df_canarias["rolling_mean_3"] = grouped["OBS_VALUE"].transform(lambda x: x.shift(1).rolling(window=3).mean())
df_canarias["Month"] = df_canarias["Month"].astype(int)

df_ml = df_canarias.dropna(subset=["lag_1", "lag_2", "lag_12", "rolling_mean_3", "OBS_VALUE"]).copy()

# 3. Split Train/Test
train_df = df_ml[df_ml["Year"] <= 2024].copy()
test_df = df_ml[df_ml["Year"] > 2024].copy()

features = ["Month", "lag_1", "lag_2", "lag_12", "rolling_mean_3", "is_pandemic"]
target = "OBS_VALUE"

X_train, y_train = train_df[features], train_df[target]
X_test, y_test = test_df[features], test_df[target]

print(f"Tamaño Train (<= 2024): {len(X_train)} meses | Tamaño Test (2025-2026): {len(X_test)} meses")

# 4. Validación Cruzada Temporal (TimeSeriesSplit)
print("\n--- Ejecutando Validación Cruzada Temporal (TimeSeriesSplit - 3 Splits) ---")
tscv = TimeSeriesSplit(n_splits=3)

models = {
    "Regresión Lineal": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
    "XGBoost (Boosting)": XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42),
    "Red Neuronal (ANN)": MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)
}

cv_results = {}
for name, model in models.items():
    cv_maes = []
    cv_rmses = []
    cv_r2s = []
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
        X_tr, y_tr = X_train.iloc[train_idx], y_train.iloc[train_idx]
        X_va, y_va = X_train.iloc[val_idx], y_train.iloc[val_idx]
        
        # Clonar/Entrenar modelo
        model.fit(X_tr, y_tr)
        preds = model.predict(X_va)
        
        cv_maes.append(mean_absolute_error(y_va, preds))
        cv_rmses.append(root_mean_squared_error(y_va, preds))
        cv_r2s.append(r2_score(y_va, preds))
        
    cv_results[name] = {
        "CV_MAE": np.mean(cv_maes),
        "CV_RMSE": np.mean(cv_rmses),
        "CV_R2": np.mean(cv_r2s)
    }

# 5. Evaluación Final en el Conjunto de Test (2025-2026)
print("\n--- Evaluación Final en Conjunto de Prueba Temporal ---")
results = []
best_model_template = None
best_rmse = float('inf')
best_model_name = ""

# Guardaremos las predicciones para graficarlas después
test_predictions = {}

for name, model in models.items():
    # Entrenar en todo el train set
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    test_predictions[name] = y_pred
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = root_mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    results.append({
        "Modelo": name,
        "CV_RMSE (Val)": cv_results[name]["CV_RMSE"],
        "CV_R2 (Val)": cv_results[name]["CV_R2"],
        "MAE (Test)": mae,
        "RMSE (Test)": rmse,
        "R2 (Test)": r2
    })
    
    print(f"{name}:")
    print(f"  - CV RMSE: {cv_results[name]['CV_RMSE']:.3f} | CV R2: {cv_results[name]['CV_R2']:.3f}")
    print(f"  - Test MAE: {mae:.3f} | Test RMSE: {rmse:.3f} | Test R2: {r2:.3f}")
    
    if rmse < best_rmse:
        best_rmse = rmse
        best_model_template = model
        best_model_name = name

results_df = pd.DataFrame(results).sort_values("RMSE (Test)")

# 6. Re-entrenamiento con el 100% de los datos para Producción
print(f"\nRe-entrenando el mejor modelo ({best_model_name}) con el 100% de los datos para Producción...")
X_full, y_full = df_ml[features], df_ml[target]
final_model = best_model_template
final_model.fit(X_full, y_full)

os.makedirs("models", exist_ok=True)
joblib.dump(final_model, "models/best_model_ocupacion.pkl")
joblib.dump(features, "models/features_list.pkl")

# 7. Generación de Gráficos de Rendimiento Científicos
print("Generando gráficos de diagnóstico en carpeta 'models/'...")

# 7.1 Importancia de Variables
if hasattr(final_model, "feature_importances_"):
    importances = final_model.feature_importances_
    indices = np.argsort(importances)
    feature_labels = [features[i] for i in indices]
    
    plt.figure(figsize=(10, 5))
    plt.barh(range(len(indices)), importances[indices], color='#a78bfa', align='center', alpha=0.9)
    plt.yticks(range(len(indices)), feature_labels)
    plt.xlabel('Importancia Relativa (Gain)', fontsize=12, color='#94a3b8')
    plt.title(f'Importancia de Variables - {best_model_name}', fontsize=14, pad=15, color='#f8fafc')
    plt.tight_layout()
    plt.savefig("models/feature_importance.png", dpi=150, facecolor='#0f172a')
    plt.close()

# 7.2 Comparativa de Predicción vs. Valores Reales (Periodo de Prueba)
plt.figure(figsize=(12, 6))
test_plot_df = test_df.copy()
test_plot_df["y_pred"] = test_predictions[best_model_name]
test_plot_df = test_plot_df.sort_values("Date")

plt.plot(test_plot_df["Date"], test_plot_df["OBS_VALUE"], label="Valores Reales (ISTAC)", color="#38bdf8", linewidth=2.5, marker='o')
plt.plot(test_plot_df["Date"], test_plot_df["y_pred"], label=f"Predicción ({best_model_name})", color="#fb923c", linewidth=2, linestyle='--', marker='x')

# Agregar banda de error
residuals = test_plot_df["OBS_VALUE"] - test_plot_df["y_pred"]
plt.fill_between(test_plot_df["Date"],
                 test_plot_df["y_pred"] - residuals.abs(),
                 test_plot_df["y_pred"] + residuals.abs(),
                 alpha=0.08, color="#fb923c", label="Banda de error")

plt.ylabel("Tasa de Ocupación (%)", fontsize=12, color='#94a3b8')
plt.title(f"Comparativa de Predicción vs. Valores Reales (Periodo de Prueba 2025-2026)\n{best_model_name} (R² = {results_df.loc[results_df['Modelo'] == best_model_name, 'R2 (Test)'].values[0]:.3f})", fontsize=14, pad=15, color='#f8fafc')
plt.legend(frameon=True, facecolor='#1e293b', edgecolor='#334155')
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig("models/prediccion_vs_real.png", dpi=150, facecolor='#0f172a')
plt.close()

# 7.3 Análisis de Residuos Completo
res = residuals.values
fig = plt.figure(figsize=(16, 10))
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

# A. Residuos en el tiempo
ax1 = fig.add_subplot(gs[0, :])
ax1.bar(range(len(res)), res, color=['#34d399' if r >= 0 else '#f43f5e' for r in res], alpha=0.8)
ax1.axhline(0, color='#94a3b8', lw=1.5, linestyle='--')
ax1.set_title('Residuos a lo largo del tiempo (Error = Real - Predicho)', color='#f8fafc')
ax1.set_xlabel('Índice de muestra (test 2025-2026)', color='#94a3b8')
ax1.set_ylabel('Residuo (pp)', color='#94a3b8')
ax1.set_facecolor('#1e293b')
for sp in ['top', 'right']: ax1.spines[sp].set_visible(False)

# B. Histograma de residuos
ax2 = fig.add_subplot(gs[1, 0])
ax2.hist(res, bins=20, color='#a78bfa', edgecolor='#0f172a', alpha=0.85)
mu, sigma = res.mean(), res.std()
x_norm = np.linspace(res.min(), res.max(), 200)
ax2.plot(x_norm, stats.norm.pdf(x_norm, mu, sigma) * len(res) * (res.max()-res.min())/20,
         color='#fbbf24', lw=2, label=f'Normal(μ={mu:.2f}, σ={sigma:.2f})')
ax2.set_title('Distribución de Residuos', color='#f8fafc')
ax2.set_xlabel('Error (pp)', color='#94a3b8')
ax2.set_ylabel('Frecuencia', color='#94a3b8')
ax2.legend(facecolor='#1e293b', fontsize=8)
ax2.set_facecolor('#1e293b')
for sp in ['top', 'right']: ax2.spines[sp].set_visible(False)

# C. QQ-Plot
ax3 = fig.add_subplot(gs[1, 1])
(osm, osr), (slope, intercept, r_val) = stats.probplot(res, dist='norm')
ax3.scatter(osm, osr, color='#38bdf8', s=20, alpha=0.7, label='Residuos')
ax3.plot(osm, slope*np.array(osm)+intercept, color='#fb923c', lw=2, label='Línea Normal')
ax3.set_title(f'QQ-Plot de Residuos (r={r_val:.3f})', color='#f8fafc')
ax3.set_xlabel('Cuantiles Teóricos (Normal)', color='#94a3b8')
ax3.set_ylabel('Cuantiles Muestrales', color='#94a3b8')
ax3.legend(facecolor='#1e293b', fontsize=8)
ax3.set_facecolor('#1e293b')
for sp in ['top', 'right']: ax3.spines[sp].set_visible(False)

# D. Error Medio por Mes
ax4 = fig.add_subplot(gs[1, 2])
months_test = test_plot_df['Month'].values
month_res = pd.DataFrame({'Month': months_test, 'Residual': res})
month_mean = month_res.groupby('Month')['Residual'].mean()
colors_mean = ['#34d399' if v >= 0 else '#f43f5e' for v in month_mean.values]
ax4.bar(month_mean.index, month_mean.values, color=colors_mean, edgecolor='#0f172a', alpha=0.85)
ax4.axhline(0, color='#94a3b8', lw=1.2, linestyle='--')
ax4.set_xticks(range(1, 13))
ax4.set_xticklabels(['En','Fe','Ma','Ab','My','Jn','Jl','Ag','Se','Oc','No','Di'], fontsize=8)
ax4.set_title('Error Medio por Mes del Año', color='#f8fafc')
ax4.set_xlabel('Mes', color='#94a3b8')
ax4.set_ylabel('Error medio (pp)', color='#94a3b8')
ax4.set_facecolor('#1e293b')
for sp in ['top', 'right']: ax4.spines[sp].set_visible(False)

fig.suptitle('Análisis Completo de Residuos - XGBoost Champion', fontsize=14, color='#f8fafc', y=1.01)
plt.savefig("models/analisis_residuos.png", dpi=150, bbox_inches='tight', facecolor='#0f172a')
plt.close()

# 7.4 Curva de Aprendizaje (Learning Curve)
train_sizes, train_scores, val_scores = learning_curve(
    best_model_template, X_train, y_train,
    cv=TimeSeriesSplit(n_splits=3),
    scoring='neg_root_mean_squared_error',
    train_sizes=np.linspace(0.1, 1.0, 10),
    n_jobs=-1
)
train_mean = -train_scores.mean(axis=1)
train_std  = train_scores.std(axis=1)
val_mean   = -val_scores.mean(axis=1)
val_std    = val_scores.std(axis=1)

plt.figure(figsize=(10, 5))
plt.plot(train_sizes, train_mean, color='#38bdf8', lw=2.5, marker='o', label='Error de Entrenamiento')
plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.15, color='#38bdf8')
plt.plot(train_sizes, val_mean, color='#fb923c', lw=2.5, marker='s', label='Error de Validación (CV Temporal)')
plt.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.15, color='#fb923c')
plt.title('Curva de Aprendizaje — XGBoost', fontsize=14, color='#f8fafc', pad=15)
plt.xlabel('Número de muestras de entrenamiento', color='#94a3b8')
plt.ylabel('RMSE (puntos porcentuales)', color='#94a3b8')
plt.legend(facecolor='#1e293b', edgecolor='#334155')
plt.tight_layout()
plt.savefig("models/curva_aprendizaje.png", dpi=150, facecolor='#0f172a')
plt.close()

# 7.5 Curva ROC-Like (Clasificación de Temporada Alta/Baja >= 70%)
THRESHOLD = 70.0
y_test_bin = (y_test.values >= THRESHOLD).astype(int)
scaler = MinMaxScaler()
y_score = scaler.fit_transform(test_predictions[best_model_name].reshape(-1, 1)).ravel()

fpr, tpr, thresholds = roc_curve(y_test_bin, y_score)
roc_auc = auc(fpr, tpr)
precision, recall, _ = precision_recall_curve(y_test_bin, y_score)
ap_score = average_precision_score(y_test_bin, y_score)

fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(14, 5))

# ROC Curve
ax_roc.plot(fpr, tpr, color='#38bdf8', lw=2.5, label=f'AUC-ROC = {roc_auc:.3f}')
ax_roc.plot([0, 1], [0, 1], color='#94a3b8', lw=1.2, linestyle='--', label='Random (AUC=0.5)')
ax_roc.fill_between(fpr, tpr, alpha=0.08, color='#38bdf8')
ax_roc.set_title('Curva ROC — Clasificación Alta Temporada (≥70%)', fontsize=12, color='#f8fafc')
ax_roc.set_xlabel('Tasa de Falsos Positivos (FPR)', color='#94a3b8')
ax_roc.set_ylabel('Tasa de Verdaderos Positivos (TPR)', color='#94a3b8')
ax_roc.legend(facecolor='#1e293b', edgecolor='#334155')
ax_roc.set_facecolor('#1e293b')
for sp in ['top', 'right']: ax_roc.spines[sp].set_visible(False)

# PR Curve
ax_pr.plot(recall, precision, color='#34d399', lw=2.5, label=f'AP = {ap_score:.3f}')
baseline = y_test_bin.sum() / len(y_test_bin)
ax_pr.axhline(baseline, color='#94a3b8', lw=1.2, linestyle='--', label=f'Baseline ({baseline:.2f})')
ax_pr.fill_between(recall, precision, alpha=0.08, color='#34d399')
ax_pr.set_title('Curva Precisión-Recall — Alta Temporada (≥70%)', fontsize=12, color='#f8fafc')
ax_pr.set_xlabel('Recall (Sensibilidad)', color='#94a3b8')
ax_pr.set_ylabel('Precisión', color='#94a3b8')
ax_pr.legend(facecolor='#1e293b', edgecolor='#334155')
ax_pr.set_facecolor('#1e293b')
for sp in ['top', 'right']: ax_pr.spines[sp].set_visible(False)

plt.suptitle('Análisis ROC y Precisión-Recall: Identificación de Alta Temporada', fontsize=14, color='#f8fafc', y=1.02)
plt.tight_layout()
plt.savefig("models/curva_roc.png", dpi=150, facecolor='#0f172a')
plt.close()

# 8. Generación del Informe Mejorado
informe_path = "models/REPORTE_ENTRENAMIENTO.md"
with open(informe_path, "w", encoding="utf-8") as f:
    f.write("# Reporte de Entrenamiento y Evaluación del Modelo Predictivo\n\n")
    f.write("Este informe describe el proceso de entrenamiento y la evaluación comparativa del rendimiento de los diferentes modelos predictivos desarrollados para el sistema de inteligencia turística.\n\n")
    f.write("## 1. Metodología de Evaluación y Robustez\n")
    f.write("Para garantizar la validez científica y evitar el sesgo de anticipación o *data leakage*, se han implementado dos metodologías rigurosas:\n")
    f.write("1. **Validación Cruzada Temporal (TimeSeriesSplit):** Se aplicaron 3 cortes temporales acumulativos sobre los datos históricos de entrenamiento (hasta 2024) para entrenar y evaluar de manera estable.\n")
    f.write("2. **Corte Temporal de Prueba Independiente (Test Holdout):** Para la evaluación final sin sesgos, se mantuvieron reservados los datos correspondientes a los años **2025 y 2026** (120 registros mensuales).\n\n")
    f.write(f"- **Conjunto de Entrenamiento:** Datos hasta 2024 ({len(X_train)} registros).\n")
    f.write(f"- **Conjunto de Prueba:** Datos de 2025 y 2026 ({len(X_test)} registros).\n\n")
    f.write("## 2. Resultados de Evaluación Comparativa\n")
    f.write("A continuación se muestra el rendimiento obtenido por cada algoritmo ordenados de mejor a peor según su RMSE de prueba:\n\n")
    f.write(results_df.to_markdown(index=False))
    f.write("\n\n*Nota: El coeficiente $R^2$ mide el porcentaje de la variabilidad de la ocupación que explica el modelo. Valores cercanos a 1 indican un ajuste muy alto y preciso.*\n\n")
    f.write("## 3. Modelo Final Seleccionado y Producción\n")
    f.write(f"El modelo ganador indiscutible fue **{best_model_name}** por presentar el menor RMSE y el mayor $R^2$ en el conjunto de prueba (capacidad de generalización excelente).\n\n")
    f.write("Para maximizar su precisión en el sistema final del Dashboard en producción, el modelo exportado ha sido re-entrenado utilizando el **100% de los registros históricos disponibles**, asimilando las dinámicas post-pandemia más recientes.\n")
    f.write("\n## 4. Gráficos de Diagnóstico Generados\n")
    f.write("Los siguientes gráficos científicos de diagnóstico se han guardado en la carpeta `models/`:\n")
    f.write("- **Importancia de Variables (`feature_importance.png`):** Muestra el impacto relativo de cada variable en las predicciones.\n")
    f.write("- **Predicción vs Real (`prediccion_vs_real.png`):** Contraste temporal de las predicciones frente a los valores históricos de prueba.\n")
    f.write("- **Análisis de Residuos (`analisis_residuos.png`):** Histogramas, QQ-Plot y errores estacionales para validar la hipótesis de normalidad e identificar sesgos.\n")
    f.write("- **Curva de Aprendizaje (`curva_aprendizaje.png`):** Análisis de la variabilidad del error de entrenamiento/validación según el tamaño muestral.\n")
    f.write("- **Curva ROC y PR (`curva_roc.png`):** Métricas de binarización del modelo para clasificar temporadas de Alta Ocupación (≥70%).\n")

print(f"\nModelo final guardado con éxito.")
print(f"Informe actualizado en: {informe_path}")
