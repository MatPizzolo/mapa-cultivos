# Mapa de Cultivos con IA

**Qué se sembró en cada lote, según dos maneras distintas de mirar el mismo satélite.**

Clasificación de cultivos sobre dos departamentos de la pampa argentina, hecha dos veces: una con
features clásicas de Sentinel-2 (bandas + índices por ventana fenológica) y otra con los
**Satellite Embeddings de AlphaEarth** (Google DeepMind). Los dos mapas se muestran uno al lado del
otro, con una cortina en el medio, y las métricas abajo. La pregunta que responde no es "¿se puede
clasificar cultivos?" —eso ya está resuelto— sino **cuánto aporta realmente un modelo fundacional de
observación de la Tierra frente al feature engineering de siempre, sobre cultivos argentinos**.

Es el Nivel 3 de una escalera de proyectos de machine learning aplicado al agro argentino
(ver [Documentos relacionados](#documentos-relacionados)).

---

## Qué se ve

| Interacción | Qué hace |
|---|---|
| **Cortina** | Los dos mapas clasificados superpuestos con un divisor arrastrable. Es la visualización del benchmark: el mismo lote, dos modelos, la diferencia a simple vista. |
| **Inspector de píxel** | Tocás cualquier punto y te dice qué clase le asignó cada modelo y qué dice el Mapa Nacional de Cultivos del INTA en ese mismo píxel. Los desacuerdos son lo interesante. |
| **Selector de zona** | Río Cuarto (Córdoba) o Pergamino (Buenos Aires). Misma leyenda, mismo pipeline, dos realidades productivas. |
| **Selector de campaña** | 2024/25 validada, o 2025/26 marcada **sin validar** — la etiqueta está en la interfaz, no escondida en un pie de página. |
| **Panel de métricas** | Accuracy, kappa y F1 por clase de los cuatro modelos, leídos de `data/metrics.json`. Se regeneran desde la corrida; nunca se escriben a mano. |
| **Explorar** *(opcional)* | Dibujás un polígono y se clasifica en vivo contra Earth Engine. Es lo único que necesita red: si falla, el resto de la app sigue entera. |

La campaña agrícola va del **1 de julio al 30 de junio**. Todo recorte temporal usa ese corte, no el
año calendario — con una excepción importante que se explica en [Datos](#datos).

## El benchmark

El documento original de la escalera proponía comparar "Random Forest con bandas contra kNN con
embeddings". Esa comparación mueve dos variables a la vez: si ganan los embeddings, no se sabe si
ganaron por las features o por el clasificador. Así que se corren las cuatro celdas:

|  | Random Forest | kNN |
|---|---|---|
| **Features clásicas** — bandas S2 + índices por ventana fenológica | A | B |
| **AlphaEarth embeddings** — 64 bandas anuales | C | D |

El resultado que importa sale de comparar **filas** (¿qué aportan los embeddings?), no la diagonal.
Correr dos celdas más cuesta dos corridas sobre la misma infraestructura, y es la diferencia entre
un benchmark y una demo.

Los números viven en [`docs/BENCHMARK.md`](docs/BENCHMARK.md). El protocolo que los hace creíbles
—muestreo, split espacial, qué se puede llamar accuracy y qué no— está en
[`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).

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
campaña. Es una desventaja real de los embeddings en este problema y el benchmark la reporta en vez
de esconderla.

Detalle de licencias, resolución y cómo se obtiene cada fuente en [`data/README.md`](data/README.md).

## Zona de cobertura

Dos departamentos elegidos porque se leen distinto, y esa diferencia *es* parte de lo que el
proyecto muestra:

| Zona | Qué la caracteriza | Qué se espera ver en la clasificación |
|---|---|---|
| **Departamento Río Cuarto** (Córdoba) | Maíz, soja y **maní**. Ciclos largos de verano, un cultivo dominante por campaña. | El maní es la clase difícil: pocas hectáreas y firma parecida a la soja temprana. Es donde el benchmark se decide. |
| **Partido de Pergamino** (Buenos Aires) | Zona núcleo clásica. Doble cultivo trigo / soja de segunda muy frecuente. | La clase `trigo/soja 2ª` debería separarse bien: son dos picos donde las demás tienen uno. Conecta directo con el Nivel 2. |

Río Cuarto va primero porque es donde es el evento. Poner las dos al lado permite mostrar en la
misma pantalla por qué un mapa de Río Cuarto no se lee igual que uno de Pergamino.

## Leyenda de clases

Las dos zonas comparten leyenda, para que las matrices de confusión sean comparables:

`soja` · `maíz` · `trigo/soja 2ª` · `maní` · `pastura/verdeo` · `no agrícola`

`trigo/soja 2ª` es **una sola clase** porque en la pampa el trigo casi siempre lleva soja de segunda
detrás: separarlos sería inventar una distinción que el píxel no sostiene. `maní` solo existe en
Río Cuarto; cómo se trata esa clase ausente en la matriz de Pergamino está en
[`docs/SPEC.md`](docs/SPEC.md).

## Stack

- **Cómputo:** Earth Engine hace muestreo, entrenamiento (`ee.Classifier.smileRandomForest`,
  `smileKnn`) e inferencia. **No se bajan rasters.**
- **Orquestación y evaluación:** Python 3.12 gestionado con `uv`. `earthengine-api` para hablar con
  GEE; scikit-learn solo para calcular métricas sobre la tabla de validación exportada. Hay un solo
  modelo, no una versión GEE y otra local que podrían diverger.
- **Backend:** FastAPI, mínimo — sirve el frontend, `metrics.json` y el modo explorar.
- **Frontend:** HTML + JS sin framework. Leaflet para el mapa y la cortina. Elegido por peso, no por
  comodidad — mismo criterio que [`../monitoring`](../monitoring/README.md).
- **Deploy:** Cloud Run, misma región que el proyecto de Earth Engine. Tiles precomputados en un
  bucket de GCS con cacheo largo.
- **Sin base de datos:** las muestras y las métricas son archivos versionados en el repo.

## Estructura

```
src/mapa_cultivos/
  settings.py       # configuración por variables de entorno
  ee_client.py      # init de Earth Engine con service account
  zonas.py          # geometrías de los departamentos y ventanas de campaña
  referencia.py     # capa del MNC del INTA: carga y remapeo a la leyenda propia
  muestras.py       # muestreo estratificado, bloques espaciales, erosión de bordes
  features.py       # clasicas() y embeddings() — los dos juegos de features
  clasificar.py     # entrena y aplica ee.Classifier — las 4 celdas del 2x2
  evaluar.py        # matriz de confusión, kappa, F1 por clase, intervalos
  exportar.py       # export del mapa clasificado y de las tablas de validación
  api/
    main.py         # FastAPI: frontend estático, /metrics, /clasificar
    schemas.py      # modelos Pydantic de request y response
scripts/
  01_muestrear.py
  02_benchmark.py   # corre el 2x2 y regenera metrics.json + docs/BENCHMARK.md
  03_exportar_mapa.py
  04_tiles.py       # GeoTIFF → tiles XYZ
data/
  zonas.geojson     # límites departamentales — única fuente de verdad
  leyenda.json      # clases, colores y mapeo desde el MNC
  muestras/         # tablas de muestreo versionadas
  metrics.json      # lo que lee el panel del frontend
frontend/
  index.html
  app.js            # mapa, cortina, inspector de píxel y panel de métricas
tests/
docs/
```

## Cómo correrlo

Requiere una cuenta de Google Cloud con la API de Earth Engine habilitada y un
[service account registrado en Earth Engine](https://developers.google.com/earth-engine/guides/service_account).

```bash
cp .env.example .env          # completar GEE_SERVICE_ACCOUNT, GEE_KEY_PATH y GCS_TILES_BUCKET
make install                  # uv sync
make dev                      # http://localhost:8000
make test

make muestras                 # 01 — regenera data/muestras/ contra Earth Engine
make benchmark                # 02 — corre las 4 celdas y reescribe metrics.json + BENCHMARK.md
make mapa                     # 03 — exporta el mapa clasificado (tarda: son exports de GEE)
make tiles                    # 04 — GeoTIFF → tiles y sube al bucket
make docker                   # build de la imagen
```

La key JSON del service account vive fuera del repo y su ruta se pasa por `GEE_KEY_PATH`.
Está en `.gitignore` y no debe entrar a git bajo ninguna circunstancia.

## Requisitos no negociables

1. **Honestidad del método por encima del número.** El Mapa Nacional de Cultivos del INTA es un
   producto de clasificación con su propio error, no verdad de campo: contra él se reporta
   **acuerdo**, nunca *accuracy*. El accuracy real se mide contra un set independiente
   fotointerpretado a mano. Las dos métricas se reportan por separado y la interfaz las distingue.
   Ver [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md).
2. **La demo no depende de la red.** Los mapas se sirven desde tiles precomputados. Si Earth Engine
   no responde, lo único que se cae es el modo explorar; la cortina, el inspector y las métricas
   siguen enteros.
3. **Reproducibilidad.** Semilla fija, muestras versionadas en el repo, y todo número publicado
   regenerable con un comando. `metrics.json` y las tablas de `BENCHMARK.md` se escriben desde la
   corrida, jamás a mano.
4. **Mobile-first real.** El uso previsto es un celular con 4G en un predio ferial.
   LCP < 2.5 s con throttling "Slow 4G" en DevTools.
5. **Peso:** carga inicial < 300 KB transferidos sin contar tiles, alineado con el resto del
   portfolio. Los tiles se cachean agresivo y se limitan a los zooms 9–13.
6. **Español primero y accesibilidad base.** Toda la interfaz en español rioplatense; el código y los
   comentarios en inglés. Contraste AA, foco visible, `prefers-reduced-motion` respetado. La paleta
   de clases tiene que ser distinguible con daltonismo — no verde contra rojo.

## Estado

El objetivo es 🟢 live para el 12 de agosto de 2026. Para que eso sea alcanzable, el alcance está
partido en capas y el orden de recorte ya está decidido de antemano:

| Capa | Qué incluye | Estado | Cae si… |
|---|---|---|---|
| **Piso** | Río Cuarto · campaña 24/25 · las 4 celdas · cortina + inspector + métricas | 🟡 En construcción | Nunca. Sin esto el proyecto no se muestra |
| **Capa 2** | Pergamino con el mismo pipeline | 🟡 En construcción | El etiquetado de muestras se estira |
| **Capa 3** | Campaña 25/26 como inferencia sin validar | 🟡 En construcción | Falta tiempo de export y tiles |
| **Capa 4** | Modo explorar en vivo contra Earth Engine | 🟡 En construcción | Primera en caer. Es lo único que depende de la red |

Cronograma día por día en [`docs/SPEC.md`](docs/SPEC.md#10-cronograma).

## Documentos relacionados

- [`docs/SPEC.md`](docs/SPEC.md) — decisiones técnicas, pipeline, contrato de la API y cronograma
- [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md) — muestreo, validación y limitaciones declaradas
- [`docs/BENCHMARK.md`](docs/BENCHMARK.md) — resultados del 2×2 y borrador del post
- [`data/README.md`](data/README.md) — fuentes de datos, licencias y qué entra a git
- [`CLAUDE.md`](CLAUDE.md) — contexto e instrucciones para trabajar en este repo con Claude Code
- [`../monitoring/README.md`](../monitoring/README.md) — Nivel 2, el hermano más cercano
- [`../portfolio/README.md`](../portfolio/README.md) — la web que linkea este proyecto
- [`../portfolio-agtech-escalera-proyectos.md`](../portfolio-agtech-escalera-proyectos.md) — la escalera completa
