# BENCHMARK — features clásicas vs Satellite Embeddings de AlphaEarth

> ⚠️ **Este archivo se regenera con `make benchmark` (`scripts/02_benchmark.py`). No se edita a
> mano.** Todo valor `PENDIENTE` o `—` es un número que todavía no corrió. Si aparece un número que
> no salió de una corrida, es un bug del proceso, no un dato.

**Estado:** 🟢 corrida completa contra el MNC · accuracy independiente `PENDIENTE`.
**Última corrida:** 2026-08-09T22:12:18Z · **Semilla:** 42

Cómo leer estos números —qué se puede llamar accuracy, qué es acuerdo, y qué no se puede concluir—
está en [`METODOLOGIA.md`](METODOLOGIA.md). Leerlo antes de citar cualquier valor de acá.

**Todos los números de este archivo son ACUERDO con el MNC, salvo donde se diga accuracy.** Los
puntos de validación independiente fotointerpretados todavía no están etiquetados; hasta entonces,
las tablas de accuracy quedan en `—` y ninguna conclusión se apoya en ellas.

---

## Setup

| | |
|---|---|
| Zonas | Departamento Río Cuarto (Córdoba) · Partido de Pergamino (Buenos Aires) |
| Campaña validada | 2024-25 (contra MNC; validación independiente `PENDIENTE`) |
| Campaña sin validar | `PENDIENTE` — objetivo 2025/26, capa 3 |
| Clases | soja · maíz · trigo/soja 2ª · maní · pastura/verdeo · no agrícola |
| Split | Bloques espaciales de 5 × 5 km, bloque entero a train o validación |
| Erosión de bordes | 1 píxel sobre la grilla del MNC (~25–30 m; la spec decía «2 px / 20 m» asumiendo dato de 10 m) |
| Resolución | Features a 10 m; referencia MNC a ~25–30 m |

### Muestras

| Zona | Entrenamiento | Validación MNC | Validación independiente | Indeterminados excluidos |
|---|---|---|---|---|
| Río Cuarto | 2500 | 1500 | `—` | `—` |
| Pergamino | 2000 | 1200 | `—` | `—` |

**Clases sin soporte en el cruce del MNC:** `pastura/verdeo` no existe en el MNC 2024/25 de ninguna
de las dos zonas (los códigos de verdeo no aparecen en los recortes) y `maní` no existe en Pergamino.
Se reportan con soporte 0 y quedan fuera de los promedios macro — no se rellenan.

### Versiones de datos

| Fuente | Versión / fecha de acceso |
|---|---|
| `COPERNICUS/S2_SR_HARMONIZED` | acceso 2026-08-09 |
| `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | acceso 2026-08-09, umbral cs ≥ 0.60 |
| `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` | acceso 2026-08-09 |
| Mapa Nacional de Cultivos (INTA) | campaña 2024/25 v1, Zenodo `10.5281/zenodo.17652712` (CC-BY-4.0), descargado 2026-08-09 |
| Accuracy que reporta el MNC para esa campaña | `PENDIENTE` — leer del informe oficial; es el techo del acuerdo |

---

## Resultado principal — el 2×2

Comparar **filas**: es la pregunta del proyecto (¿qué aportan los embeddings?). Comparar columnas
responde otra cosa (¿qué clasificador anda mejor?) y es secundaria.

### Río Cuarto — accuracy independiente, IC 95 %

`PENDIENTE` — faltan los puntos fotointerpretados.

### Río Cuarto — acuerdo con el MNC

*Acuerdo, no accuracy. Ver [`METODOLOGIA.md → 1`](METODOLOGIA.md#1-el-mapa-nacional-de-cultivos-es-referencia-no-verdad-de-campo).*

| | Random Forest | kNN |
|---|---|---|
| **Clásicas** (89 features) | 94.3 % | 94.5 % |
| **Embeddings** (128 features) | 91.1 % | 90.6 % |

### Pergamino — accuracy independiente, IC 95 %

`PENDIENTE` — faltan los puntos fotointerpretados.

### Pergamino — acuerdo con el MNC

| | Random Forest | kNN |
|---|---|---|
| **Clásicas** (89 features) | 94.7 % | 94.4 % |
| **Embeddings** (128 features) | 93.0 % | 92.9 % |

### Kappa

Se reporta porque se espera verlo. **Ninguna conclusión se apoya en kappa** — ver
[`METODOLOGIA.md → 5.2`](METODOLOGIA.md#52-sobre-kappa).

| Zona | clásicas-rf | clásicas-knn | embeddings-rf | embeddings-knn |
|---|---|---|---|---|
| Río Cuarto | 0.929 | 0.931 | 0.889 | 0.882 |
| Pergamino | 0.929 | 0.926 | 0.907 | 0.906 |

### ¿Las diferencias son reales?

Test de McNemar sobre aciertos pareados. `p ≥ 0.05` significa **"no se distinguen con esta muestra"**,
y eso es lo que se publica — no el modelo que quedó medio punto arriba.

| Zona | Comparación | Δ acuerdo | p (McNemar) | Conclusión |
|---|---|---|---|---|
| Río Cuarto | clasicas-rf vs embeddings-rf | +3.2 pp | 0.0001 | difieren |
| Río Cuarto | clasicas-knn vs embeddings-knn | +3.9 pp | 0.0000 | difieren |
| Pergamino | clasicas-rf vs embeddings-rf | +1.7 pp | 0.0265 | difieren |
| Pergamino | clasicas-knn vs embeddings-knn | +1.5 pp | 0.0414 | difieren |

---

## Matrices de confusión

Filas = referencia (MNC), columnas = predicción. Las de Pergamino conservan la fila y la columna de
`maní` vacías: la clase no existe en esa zona y se excluye del promedio macro, no se cuenta como
cero. Ídem `pastura/verdeo` en las dos zonas.

### Río Cuarto · clasicas-rf

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 290 | 1 | 8 | 1 | 0 | 0 |
| soja | 2 | 265 | 11 | 4 | 18 | 0 |
| maíz | 2 | 8 | 283 | 7 | 0 | 0 |
| trigo/soja 2ª | 0 | 14 | 1 | 285 | 0 | 0 |
| maní | 0 | 8 | 0 | 0 | 292 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Río Cuarto · clasicas-knn

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 292 | 1 | 4 | 0 | 3 | 0 |
| soja | 2 | 266 | 7 | 6 | 19 | 0 |
| maíz | 6 | 20 | 269 | 3 | 2 | 0 |
| trigo/soja 2ª | 0 | 6 | 1 | 293 | 0 | 0 |
| maní | 0 | 3 | 0 | 0 | 297 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Río Cuarto · embeddings-rf

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 293 | 0 | 5 | 2 | 0 | 0 |
| soja | 0 | 253 | 6 | 8 | 33 | 0 |
| maíz | 2 | 7 | 286 | 2 | 3 | 0 |
| trigo/soja 2ª | 1 | 29 | 2 | 264 | 4 | 0 |
| maní | 1 | 22 | 0 | 6 | 271 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Río Cuarto · embeddings-knn

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 289 | 0 | 5 | 6 | 0 | 0 |
| soja | 0 | 223 | 4 | 15 | 58 | 0 |
| maíz | 2 | 10 | 278 | 1 | 9 | 0 |
| trigo/soja 2ª | 0 | 14 | 0 | 282 | 4 | 0 |
| maní | 0 | 10 | 1 | 2 | 287 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Pergamino · clasicas-rf

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 288 | 6 | 1 | 5 | 0 | 0 |
| soja | 10 | 284 | 6 | 0 | 0 | 0 |
| maíz | 7 | 15 | 276 | 2 | 0 | 0 |
| trigo/soja 2ª | 8 | 4 | 0 | 288 | 0 | 0 |
| maní | 0 | 0 | 0 | 0 | 0 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Pergamino · clasicas-knn

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 288 | 8 | 1 | 3 | 0 | 0 |
| soja | 6 | 279 | 8 | 7 | 0 | 0 |
| maíz | 8 | 14 | 277 | 1 | 0 | 0 |
| trigo/soja 2ª | 5 | 5 | 1 | 289 | 0 | 0 |
| maní | 0 | 0 | 0 | 0 | 0 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Pergamino · embeddings-rf

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 285 | 13 | 0 | 2 | 0 | 0 |
| soja | 9 | 268 | 7 | 16 | 0 | 0 |
| maíz | 1 | 18 | 280 | 1 | 0 | 0 |
| trigo/soja 2ª | 7 | 8 | 2 | 283 | 0 | 0 |
| maní | 0 | 0 | 0 | 0 | 0 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

### Pergamino · embeddings-knn

| ref \ pred | no agrícola | soja | maíz | trigo/soja 2ª | maní | pastura/verdeo |
|---|---|---|---|---|---|---|
| no agrícola | 282 | 12 | 3 | 3 | 0 | 0 |
| soja | 4 | 267 | 11 | 18 | 0 | 0 |
| maíz | 3 | 10 | 283 | 4 | 0 | 0 |
| trigo/soja 2ª | 1 | 11 | 5 | 283 | 0 | 0 |
| maní | 0 | 0 | 0 | 0 | 0 | 0 |
| pastura/verdeo | 0 | 0 | 0 | 0 | 0 | 0 |

---

## Por clase

F1, producer's y user's accuracy, con soporte al lado — un F1 sin soporte no se lee. `maní` va en
negrita porque es la clase que decide el benchmark.

### Río Cuarto

| Clase | Modelo | F1 | Producer's | User's | Soporte |
|---|---|---|---|---|---|
| no agrícola | clasicas-rf | 0.976 | 0.967 | 0.986 | 300 |
| no agrícola | clasicas-knn | 0.973 | 0.973 | 0.973 | 300 |
| no agrícola | embeddings-rf | 0.982 | 0.977 | 0.987 | 300 |
| no agrícola | embeddings-knn | 0.978 | 0.963 | 0.993 | 300 |
| soja | clasicas-rf | 0.889 | 0.883 | 0.895 | 300 |
| soja | clasicas-knn | 0.893 | 0.887 | 0.899 | 300 |
| soja | embeddings-rf | 0.828 | 0.843 | 0.814 | 300 |
| soja | embeddings-knn | 0.801 | 0.743 | 0.868 | 300 |
| maíz | clasicas-rf | 0.939 | 0.943 | 0.934 | 300 |
| maíz | clasicas-knn | 0.926 | 0.897 | 0.957 | 300 |
| maíz | embeddings-rf | 0.955 | 0.953 | 0.957 | 300 |
| maíz | embeddings-knn | 0.946 | 0.927 | 0.965 | 300 |
| trigo/soja 2ª | clasicas-rf | 0.955 | 0.950 | 0.960 | 300 |
| trigo/soja 2ª | clasicas-knn | 0.973 | 0.977 | 0.970 | 300 |
| trigo/soja 2ª | embeddings-rf | 0.907 | 0.880 | 0.936 | 300 |
| trigo/soja 2ª | embeddings-knn | 0.931 | 0.940 | 0.922 | 300 |
| **maní** | clasicas-rf | 0.957 | 0.973 | 0.942 | 300 |
| **maní** | clasicas-knn | 0.957 | 0.990 | 0.925 | 300 |
| **maní** | embeddings-rf | 0.887 | 0.903 | 0.871 | 300 |
| **maní** | embeddings-knn | 0.872 | 0.957 | 0.802 | 300 |
| pastura/verdeo | clasicas-rf | `—` | `—` | `—` | 0 |
| pastura/verdeo | clasicas-knn | `—` | `—` | `—` | 0 |
| pastura/verdeo | embeddings-rf | `—` | `—` | `—` | 0 |
| pastura/verdeo | embeddings-knn | `—` | `—` | `—` | 0 |

### Pergamino

| Clase | Modelo | F1 | Producer's | User's | Soporte |
|---|---|---|---|---|---|
| no agrícola | clasicas-rf | 0.940 | 0.960 | 0.920 | 300 |
| no agrícola | clasicas-knn | 0.949 | 0.960 | 0.938 | 300 |
| no agrícola | embeddings-rf | 0.947 | 0.950 | 0.944 | 300 |
| no agrícola | embeddings-knn | 0.956 | 0.940 | 0.972 | 300 |
| soja | clasicas-rf | 0.933 | 0.947 | 0.919 | 300 |
| soja | clasicas-knn | 0.921 | 0.930 | 0.912 | 300 |
| soja | embeddings-rf | 0.883 | 0.893 | 0.873 | 300 |
| soja | embeddings-knn | 0.890 | 0.890 | 0.890 | 300 |
| maíz | clasicas-rf | 0.947 | 0.920 | 0.975 | 300 |
| maíz | clasicas-knn | 0.944 | 0.923 | 0.965 | 300 |
| maíz | embeddings-rf | 0.951 | 0.933 | 0.969 | 300 |
| maíz | embeddings-knn | 0.940 | 0.943 | 0.937 | 300 |
| trigo/soja 2ª | clasicas-rf | 0.968 | 0.960 | 0.976 | 300 |
| trigo/soja 2ª | clasicas-knn | 0.963 | 0.963 | 0.963 | 300 |
| trigo/soja 2ª | embeddings-rf | 0.940 | 0.943 | 0.937 | 300 |
| trigo/soja 2ª | embeddings-knn | 0.931 | 0.943 | 0.919 | 300 |
| **maní** | clasicas-rf | `—` | `—` | `—` | 0 |
| **maní** | clasicas-knn | `—` | `—` | `—` | 0 |
| **maní** | embeddings-rf | `—` | `—` | `—` | 0 |
| **maní** | embeddings-knn | `—` | `—` | `—` | 0 |
| pastura/verdeo | clasicas-rf | `—` | `—` | `—` | 0 |
| pastura/verdeo | clasicas-knn | `—` | `—` | `—` | 0 |
| pastura/verdeo | embeddings-rf | `—` | `—` | `—` | 0 |
| pastura/verdeo | embeddings-knn | `—` | `—` | `—` | 0 |

---

## Ablaciones

Cada una aísla una decisión de método. Son resultados por derecho propio, no notas al pie.

### A. El desfase calendario / campaña de los embeddings

Configuración principal: embeddings de los **dos** años calendario que solapan la campaña (128
features). Ablación: **solo el segundo año**, el del verano (64 features). Ambas con RF.

| Zona | Dos años (128) | Un año (64) | Δ |
|---|---|---|---|
| Río Cuarto | 91.1 % | 86.8 % | -4.3 pp |
| Pergamino | 93.0 % | 89.0 % | -4.0 pp |

Cuantifica cuánto cuesta que el dataset esté indexado por año calendario y la campaña no lo esté.
Ver [`METODOLOGIA.md → 7.1`](METODOLOGIA.md#7-limitaciones-declaradas).

### B. Cuánto infla el split aleatorio

Mismo modelo, misma muestra, dos maneras de partirla.

| Zona | Modelo | Bloques 5 km | Aleatorio | Δ (inflación) |
|---|---|---|---|---|
| Río Cuarto | clasicas-rf | 94.3 % | 94.3 % | +0.0 pp |
| Río Cuarto | embeddings-rf | 91.1 % | 92.5 % | +1.4 pp |

Sirve para comparar contra benchmarks publicados con split aleatorio, que es la mayoría.

---

## Superficie sembrada estimada

`PENDIENTE` — la corrección por matriz de error (Olofsson et al., 2014) se calcula después de la
validación independiente; hacerla contra el acuerdo con el MNC mediría el área del MNC, no la
del mapa.

---

## Lectura de los resultados

`PENDIENTE` — se escribe a mano después de revisar esta corrida (es interpretación, no dato: es la
única sección de este archivo que se edita, y el regenerador la pisa marcada como pendiente hasta
que exista la validación independiente).

## Cómo reproducir

```bash
cp .env.example .env    # GEE_SERVICE_ACCOUNT, GEE_KEY_PATH, MNC_DIR
make install
make muestras           # solo si cambian las zonas o la campaña
make benchmark          # corre las 4 celdas + ablaciones y reescribe este archivo
```

Las muestras están versionadas en `data/muestras/`, así que `make benchmark` reproduce estos números
exactos sin volver a muestrear. La semilla es 42 y está en `settings.py`.
