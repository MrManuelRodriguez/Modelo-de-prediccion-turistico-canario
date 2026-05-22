# Reporte de Entrenamiento y Evaluación del Modelo Predictivo

Este informe describe el proceso de entrenamiento y la evaluación comparativa del rendimiento de los diferentes modelos predictivos desarrollados para el sistema de inteligencia turística.

## 1. Metodología de Evaluación y Robustez
Para garantizar la validez científica y evitar el sesgo de anticipación o *data leakage*, se han implementado dos metodologías rigurosas:
1. **Validación Cruzada Temporal (TimeSeriesSplit):** Se aplicaron 3 cortes temporales acumulativos sobre los datos históricos de entrenamiento (hasta 2024) para entrenar y evaluar de manera estable.
2. **Corte Temporal de Prueba Independiente (Test Holdout):** Para la evaluación final sin sesgos, se mantuvieron reservados los datos correspondientes a los años **2025 y 2026** (120 registros mensuales).

- **Conjunto de Entrenamiento:** Datos hasta 2024 (1415 registros).
- **Conjunto de Prueba:** Datos de 2025 y 2026 (120 registros).

## 2. Resultados de Evaluación Comparativa
A continuación se muestra el rendimiento obtenido por cada algoritmo ordenados de mejor a peor según su RMSE de prueba:

| Modelo             |   CV_RMSE (Val) |   CV_R2 (Val) |   MAE (Test) |   RMSE (Test) |   R2 (Test) |
|:-------------------|----------------:|--------------:|-------------:|--------------:|------------:|
| XGBoost (Boosting) |         4.32396 |      0.898732 |      1.61587 |       2.08655 |    0.91536  |
| Random Forest      |         4.34421 |      0.903966 |      1.6529  |       2.22695 |    0.903586 |
| Red Neuronal (ANN) |         6.15285 |      0.821633 |      2.32809 |       2.9524  |    0.830538 |
| Regresión Lineal   |         6.85298 |      0.778472 |      3.57041 |       4.36658 |    0.629317 |

*Nota: El coeficiente $R^2$ mide el porcentaje de la variabilidad de la ocupación que explica el modelo. Valores cercanos a 1 indican un ajuste muy alto y preciso.*

## 3. Modelo Final Seleccionado y Producción
El modelo ganador indiscutible fue **XGBoost (Boosting)** por presentar el menor RMSE y el mayor $R^2$ en el conjunto de prueba (capacidad de generalización excelente).

Para maximizar su precisión en el sistema final del Dashboard en producción, el modelo exportado ha sido re-entrenado utilizando el **100% de los registros históricos disponibles**, asimilando las dinámicas post-pandemia más recientes.

## 4. Gráficos de Diagnóstico Generados
Los siguientes gráficos científicos de diagnóstico se han guardado en la carpeta `models/`:
- **Importancia de Variables (`feature_importance.png`):** Muestra el impacto relativo de cada variable en las predicciones.
- **Predicción vs Real (`prediccion_vs_real.png`):** Contraste temporal de las predicciones frente a los valores históricos de prueba.
- **Análisis de Residuos (`analisis_residuos.png`):** Histogramas, QQ-Plot y errores estacionales para validar la hipótesis de normalidad e identificar sesgos.
- **Curva de Aprendizaje (`curva_aprendizaje.png`):** Análisis de la variabilidad del error de entrenamiento/validación según el tamaño muestral.
- **Curva ROC y PR (`curva_roc.png`):** Métricas de binarización del modelo para clasificar temporadas de Alta Ocupación (≥70%).
