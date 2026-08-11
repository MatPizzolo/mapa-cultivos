# Mapa de cultivos con IA

[English](README.en.md)

**Qué se sembró en cada lote, según dos maneras distintas de mirar el mismo satélite.**

Clasificación de cultivos sobre dos departamentos de la pampa argentina, hecha dos veces: una con
features clásicas de Sentinel-2 (bandas + índices por ventana fenológica) y otra con los
**Satellite Embeddings de AlphaEarth** (Google DeepMind). Los dos mapas se muestran uno al lado del
otro, con una cortina en el medio, y las métricas abajo. La pregunta que responde no es "¿se puede
clasificar cultivos?" —eso ya está resuelto— sino **cuánto aporta realmente un modelo fundacional de
observación de la Tierra frente al feature engineering de siempre, sobre cultivos argentinos**.

El proyecto no es el mapa: es el benchmark. El mapa es cómo se muestra.

---

## Qué se ve

| Interacción | Qué hace |
|---|---|
| **Cortina** | Los dos mapas clasificados superpuestos con un divisor arrastrable. Es la visualización del benchmark: el mismo lote, dos juegos de features, la diferencia a simple vista. |
| **Inspector de píxel** | Tocás cualquier punto y te dice qué clase le asignó cada modelo y qué dice el Mapa Nacional de Cultivos del INTA en ese mismo píxel. Los desacuerdos son lo interesante. |
| **Modo desacuerdos** | Una capa que pinta solo los píxeles donde los dos juegos de features no coinciden, con el porcentaje por zona y clasificador leído de `data/desacuerdo.json`. |
| **Tour de casos** | Chips que llevan a parches de desacuerdo concretos, elegidos con `scripts/06_casos.py` sobre las componentes conexas más grandes. Sirve para no dejar al visitante buscando a ojo. |
| **Selector de zona** | Río Cuarto (Córdoba) o Pergamino (Buenos Aires). Misma leyenda, mismo pipeline, dos realidades productivas. |
| **Selector de campaña** | 2024/25 validada, o 2025/26 marcada **sin validar** — la etiqueta aparece en una banda de la interfaz, no escondida en un pie de página. |
| **Panel de métricas** | Acuerdo, kappa y F1 por clase de los cuatro modelos, leídos de `data/metrics.json`. Un valor faltante se renderiza `—`, nunca un cero. |
| **Explorar** | Dibujás un polígono y se clasifica en vivo contra Earth Engine. Es lo único que necesita red; si falla, el resto de la app sigue entera. Hoy responde `503` (ver [Estado](#estado)). |

La campaña agrícola va del **1 de julio al 30 de junio**. Todo recorte temporal usa ese corte, no el
año calendario — con una excepción importante que se explica en [Datos](#datos).

## El benchmark

El planteo obvio sería comparar "Random Forest con bandas contra kNN con embeddings". Esa comparación
mueve dos variables a la vez: si ganan los embeddings, no se sabe si ganaron por las features o por
el clasificador. Así que se corren las cuatro celdas:

|  | Random Forest | kNN |
|---|---|---|
| **Features clásicas** — bandas S2 + índices por ventana fenológica (89 features) | A | B |
| **AlphaEarth embeddings** — 64 bandas anuales, dos años (128 features) | C | D |

El resultado que importa sale de comparar **filas** (¿qué aportan los embeddings?), no la diagonal.
Correr dos celdas más cuesta dos corridas sobre la misma infraestructura, y es la diferencia entre un
benchmark y una demo.

### Resultado de la corrida actual

Acuerdo con el MNC, campaña 2024/25:

| Zona | clásicas-RF | clásicas-kNN | embeddings-RF | embeddings-kNN |
|---|---|---|---|---|
| Río Cuarto | 94.3 % | 94.5 % | 91.1 % | 90.6 % |
| Pergamino | 94.7 % | 94.4 % | 93.0 % | 92.9 % |

**Las features clásicas ganan en las dos zonas**, y el test de McNemar sobre aciertos pareados dice
que las diferencias no son ruido (`p < 0.05` en las cuatro comparaciones por fila). La brecha se
concentra donde se esperaba: `maní` en Río Cuarto cae de 0.957 a 0.887 de F1, confundiéndose con
soja. Es el resultado contrario al que promete el enfoque de moda, y es el que se publica.

Dos ablaciones acompañan el número principal: usar embeddings de un solo año calendario en vez de dos
cuesta ~4 pp, y el split aleatorio infla el acuerdo hasta 1.4 pp frente al split por bloques
espaciales — útil para comparar contra benchmarks publicados, que casi siempre usan split aleatorio.

Los números completos —matrices de confusión, F1 por clase con soporte, intervalos— viven en
[`docs/BENCHMARK.md`](docs/BENCHMARK.md), regenerado por `make benchmark` y nunca editado a mano.

### Acuerdo no es accuracy

El Mapa Nacional de Cultivos del INTA es un producto de clasificación con su propio error, no verdad
de campo. Contra él se reporta **acuerdo**; la palabra *accuracy* queda reservada para un set
independiente fotointerpretado a mano, que todavía no está etiquetado. Hasta que exista, las tablas
de accuracy quedan en `—` y ninguna conclusión se apoya en ellas. La distinción está en el código, en
los docs y en los strings de la interfaz. El protocolo completo —muestreo, split, qué se puede
concluir y qué no— está en [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).

### Reproducibilidad

Semilla fija (`SEED = 42` en `settings.py`), muestras versionadas en `data/muestras/`, y todo número
publicado regenerable con un comando. `data/metrics.json`, `data/desacuerdo.json` y las tablas de
`BENCHMARK.md` se escriben desde la corrida: si hay que tocarlos a mano, el bug está en el script.
Cambiar la semilla para mejorar un número está prohibido — si el resultado se mueve entre semillas,
esa varianza es el hallazgo.

## Datos

| Colección | Para qué | Desde |
|---|---|---|
| `COPERNICUS/S2_SR_HARMONIZED` | Reflectancia de superficie para las features clásicas, 10 m | 2017-03-28 |
| `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | Enmascarado de nubes y sombras. Banda `cs`, se descarta por debajo de 0.60 | 2015-06-27 |
| `GOOGLE/SATELLITE_EMBEDDING` | Embeddings de AlphaEarth, 64 bandas, 10 m, **anuales por año calendario** | 2017 |
| Mapa Nacional de Cultivos — INTA / GeoINTA | Capa de referencia y base del muestreo estratificado | campaña 2018/19 |
| Límites departamentales — IGN | Geometrías de Río Cuarto y Pergamino | — |

**El desfase que hay que nombrar:** los embeddings de AlphaEarth son anuales por **año calendario**,
y la campaña agrícola no lo es. El embedding de 2025 cubre el final de la campaña 24/25 y el arranque
de la 25/26 mezclados en el mismo vector. Las features clásicas sí se recortan a la ventana exacta de
campaña. Es una desventaja real de los embeddings en este problema, y el benchmark la mide (ablación
A) en vez de esconderla.

Detalle de licencias, resolución y cómo se obtiene cada fuente en [`data/README.md`](data/README.md).

## Zona de cobertura

Dos departamentos elegidos porque se leen distinto, y esa diferencia *es* parte de lo que el proyecto
muestra:

| Zona | Qué la caracteriza | Qué se espera ver en la clasificación |
|---|---|---|
| **Departamento Río Cuarto** (Córdoba) | Maíz, soja y **maní**. Ciclos largos de verano, un cultivo dominante por campaña. | El maní es la clase difícil: pocas hectáreas y firma parecida a la soja temprana. Es donde el benchmark se decide. |
| **Partido de Pergamino** (Buenos Aires) | Zona núcleo clásica. Doble cultivo trigo / soja de segunda muy frecuente. | La clase `trigo/soja 2ª` debería separarse bien: son dos picos donde las demás tienen uno. |

Río Cuarto es la zona por defecto porque es la que tiene maní, la clase minoritaria que separa a los
dos juegos de features. Poner las dos al lado permite mostrar en la misma pantalla por qué un mapa de
Río Cuarto no se lee igual que uno de Pergamino.

## Leyenda de clases

Las dos zonas comparten leyenda, para que las matrices de confusión sean comparables:

`soja` · `maíz` · `trigo/soja 2ª` · `maní` · `pastura/verdeo` · `no agrícola`

`trigo/soja 2ª` es **una sola clase** porque en la pampa el trigo casi siempre lleva soja de segunda
detrás: separarlos sería inventar una distinción que el píxel no sostiene. `maní` solo existe en Río
Cuarto y `pastura/verdeo` no aparece en el MNC 2024/25 de ninguna de las dos zonas: las dos se
reportan con soporte 0 y quedan fuera de los promedios macro, no se rellenan con ceros. Códigos,
colores y mapeo desde el MNC están en `data/leyenda.json`, fuente de verdad única; la paleta tiene
que ser distinguible con daltonismo, y el par riesgoso es soja/maní.

## Stack

- **Cómputo:** Earth Engine hace muestreo, entrenamiento (`ee.Classifier.smileRandomForest`,
  `smileKnn`) e inferencia. **No se bajan rasters.**
- **Orquestación y evaluación:** Python 3.12 gestionado con `uv`. `earthengine-api` para hablar con
  GEE; scikit-learn solo para calcular métricas sobre la tabla de validación exportada. Hay un solo
  modelo, no una versión GEE y otra local que podrían diverger.
- **Backend:** FastAPI, mínimo — sirve el frontend, los JSON de datos y el modo explorar. Todo lo que
  puede ser estático se sirve estático.
- **Frontend:** HTML + JS sin framework, Leaflet vendorizado para el mapa y la cortina. Sin build: lo
  que se lee en `frontend/app.js` es lo que corre.
- **La demo no depende de la red.** Los mapas se sirven desde tiles precomputados en un bucket de GCS
  con cacheo largo, limitados a los zooms 9–13. Si Earth Engine no responde, lo único que se cae es
  el modo explorar; la cortina, el inspector y las métricas siguen enteros. Y si los tiles tampoco
  cargan, el visor explica por qué en vez de fallar mudo.
- **Deploy:** Cloud Run, misma región que el proyecto de Earth Engine.
- **Sin base de datos:** las muestras y las métricas son archivos versionados en el repo.

## API

Base: `http://localhost:8000`. `docs_url` y `redoc_url` están deshabilitados a propósito: la API es
un detalle de implementación del visor, no un producto aparte.

| Método | Ruta | Qué devuelve |
|---|---|---|
| `GET` | `/health` | `{"status": "ok", "ee": bool}`. `ee: false` **no** degrada la app: solo el modo explorar depende de Earth Engine |
| `GET` | `/metrics` | `data/metrics.json` — lo que dibuja el panel de métricas |
| `GET` | `/leyenda` | `data/leyenda.json` — clases, colores y mapeo desde el MNC |
| `GET` | `/zonas` | `data/zonas.geojson` — límites departamentales |
| `GET` | `/desacuerdo` | `data/desacuerdo.json` — porcentaje de desacuerdo por zona y clasificador |
| `POST` | `/clasificar` | Modo explorar. Hoy devuelve `503` con un mensaje explícito, que el frontend muestra como aviso |

`/` sirve el frontend estático y `/tiles` monta los tiles locales si existe el directorio; en
producción el frontend apunta directo al bucket y ese mount no sirve nada.

## Estructura

```
src/mapa_cultivos/
  settings.py       # configuración por variables de entorno + SEED
  ee_client.py      # init de Earth Engine con service account
  zonas.py          # geometrías de los departamentos y ventanas de campaña
  referencia.py     # capa del MNC del INTA: carga y remapeo a la leyenda propia
  muestras.py       # muestreo estratificado, bloques espaciales, erosión de bordes
  features.py       # clasicas() y embeddings() — los dos juegos de features
  clasificar.py     # entrena y aplica ee.Classifier — las 4 celdas del 2x2
  evaluar.py        # matriz de confusión, kappa, F1 por clase, McNemar, intervalos
  exportar.py       # export del mapa clasificado y de las tablas de validación
  desacuerdo.py     # cruce de dos mapas exportados → máscara y porcentaje
  tiles.py          # GeoTIFF → tiles XYZ
  api/
    main.py         # FastAPI: frontend estático, JSON de datos, /clasificar
    schemas.py      # modelos Pydantic de request y response
scripts/
  01_muestrear.py
  02_benchmark.py   # corre el 2x2 + ablaciones y regenera metrics.json + BENCHMARK.md
  03_exportar_mapa.py
  04_tiles.py       # GeoTIFF → tiles XYZ
  05_desacuerdo.py  # tiles de desacuerdo + data/desacuerdo.json
  06_casos.py       # exploratorio: candidatos para el tour de casos
data/
  zonas.geojson     # límites departamentales — única fuente de verdad
  leyenda.json      # clases, colores y mapeo desde el MNC
  muestras/         # tablas de muestreo versionadas
  metrics.json      # lo que lee el panel del frontend
  desacuerdo.json   # porcentajes de desacuerdo por zona y clasificador
frontend/
  index.html
  app.js            # mapa, cortina, inspector, panel de métricas y tour de casos
  vendor/           # Leaflet y leaflet-side-by-side, vendorizados
tests/
docs/
```

## Cómo correrlo

Requiere una cuenta de Google Cloud con la API de Earth Engine habilitada y un
[service account registrado en Earth Engine](https://developers.google.com/earth-engine/guides/service_account)
—registrarlo es un paso aparte de crearlo—.

```bash
cp .env.example .env          # completar las variables de abajo
make install                  # uv sync
make dev                      # http://localhost:8000
make test

make muestras                 # 01 — regenera data/muestras/ contra Earth Engine
make benchmark                # 02 — corre las 4 celdas y reescribe metrics.json + BENCHMARK.md
make mapa                     # 03 — exporta el mapa clasificado (tarda: son exports de GEE)
make tiles                    # 04 — GeoTIFF → tiles y sube al bucket
make docker                   # build de la imagen
```

Los scripts `05` y `06` no tienen atajo en el `Makefile` porque toman rutas de exports como
argumento: `uv run python scripts/05_desacuerdo.py --exports-dir <ruta> --corrida <id>`.

### Variables de entorno

| Variable | Default | Para qué |
|---|---|---|
| `GEE_SERVICE_ACCOUNT` | — | Service account registrado en Earth Engine |
| `GEE_KEY_PATH` | — | Ruta a la key JSON, **fuera del repo** |
| `GCS_TILES_BUCKET` | — | Bucket de tiles, con lectura pública y CORS |
| `MNC_CAMPANIA` | `2024-25` | Campaña del MNC contra la que se muestrea. Es un parámetro, no una constante: si esa campaña no está publicada, se cae a la última disponible |
| `MNC_DIR` | `~/.gee/mnc` | Directorio con los rásters nacionales del MNC bajados de Zenodo. Viven fuera del repo: no entran GeoTIFFs a git |

`MNC_DIR` tiene default en `settings.py` y no está en `.env.example`. La key del service account está
en `.gitignore` y no debe entrar a git bajo ninguna circunstancia.

## Tests

```bash
make test     # 28 tests
```

Cubren la API (rutas y contratos), el remapeo de la capa de referencia, las geometrías de zonas, el
armado de tiles, el cruce de desacuerdo y la consistencia de la leyenda. No tocan Earth Engine: el
pipeline contra GEE se valida corriéndolo.

## Estado

El alcance está partido en capas, y el orden de recorte está decidido de antemano:

| Capa | Qué incluye | Estado |
|---|---|---|
| **Piso** | Río Cuarto · campaña 24/25 · las 4 celdas · cortina + inspector + métricas | Benchmark corrido y publicado en `BENCHMARK.md`; el visor funciona contra los tiles |
| **Capa 2** | Pergamino con el mismo pipeline | Corrido: métricas de las 4 celdas para las dos zonas |
| **Capa 3** | Campaña 25/26 como inferencia sin validar | El selector existe y la banda de "sin validar" también; falta la corrida |
| **Capa 4** | Modo explorar en vivo contra Earth Engine | Sin implementar. `POST /clasificar` devuelve `503` con el motivo |

Pendientes conocidos, todos declarados como `PENDIENTE` en los docs en vez de rellenados con valores
plausibles:

- **Validación independiente:** faltan los ~200 puntos fotointerpretados a mano. Hasta que existan,
  no hay accuracy — solo acuerdo — y tampoco superficie sembrada estimada, porque la corrección por
  matriz de error (Olofsson et al., 2014) se calcula contra la validación independiente.
- **Infraestructura:** el service account de GEE y el bucket público de tiles quedan como `TODO` en
  `settings.py`.
- **Accuracy auto-reportada del MNC** para la campaña 2024/25, que es el techo del acuerdo posible.

## Documentos relacionados

- [`docs/SPEC.md`](docs/SPEC.md) — decisiones técnicas, pipeline y contrato de la API
- [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md) — muestreo, validación y limitaciones declaradas
- [`docs/BENCHMARK.md`](docs/BENCHMARK.md) — resultados completos del 2×2 y las ablaciones
- [`data/README.md`](data/README.md) — fuentes de datos, licencias y qué entra a git
- [`../monitor-cultivos-ndvi/README.md`](../monitor-cultivos-ndvi/README.md) — NDVI por lote campaña
  a campaña, sobre las mismas imágenes Sentinel-2
