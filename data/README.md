# Datos

Fuentes, licencias y qué entra a git. Cómo se usa cada una está en
[`../docs/SPEC.md`](../docs/SPEC.md); por qué se eligió, en
[`../docs/METODOLOGIA.md`](../docs/METODOLOGIA.md).

---

## Resumen

| Fuente | Rol | Resolución | Cobertura temporal |
|---|---|---|---|
| `COPERNICUS/S2_SR_HARMONIZED` | Features clásicas | 10–20 m | desde 2017-03-28 |
| `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | Enmascarado de nubes | 10 m | desde 2015-06-27 |
| `GOOGLE/SATELLITE_EMBEDDING` | Features de embeddings | 10 m | anual desde 2017 |
| Mapa Nacional de Cultivos (INTA) | Referencia y muestreo | 30 m nominal | por campaña, desde 2018/19 |
| Límites departamentales (IGN) | Geometrías de las zonas | vectorial | — |
| Estimaciones Agrícolas (MAGyP) | Contraste de superficie | departamental | series largas |

---

## Sentinel-2 — `COPERNICUS/S2_SR_HARMONIZED`

Reflectancia de superficie (L2A), armonizada para corregir el salto de offset de la Colección 1.

- **Bandas usadas:** `B2 B3 B4 B5 B6 B7 B8 B8A B11 B12`. Las de 20 m se remuestrean a 10 m.
- **Escala:** los valores vienen ×10.000. Se dividen antes de calcular índices.
- **Filtrado:** por la ventana exacta de campaña (1 de julio – 30 de junio) y por la geometría de la
  zona.
- **Licencia:** Copernicus, uso libre con atribución. © European Union, Copernicus Sentinel data.
- **Límite real de la serie:** la primera campaña completa disponible es la **2017/18**. No es una
  restricción para este proyecto, que trabaja sobre 2024/25 y 2025/26.

## Cloud Score+ — `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`

Enmascarado de nubes y sombras. Reemplaza a `QA60` y a `s2cloudless`, que dejan pasar bruma y
sombras de nube — justo lo que arruina un composite de mediana.

- **Banda:** `cs`. Se descarta todo píxel con `cs < 0.60`.
- **Por qué 0.60:** es el mismo umbral que usa
  [`../../monitor-cultivos-ndvi`](../../monitor-cultivos-ndvi/README.md),
  elegido a propósito para que los dos proyectos del portfolio sean comparables entre sí. Un umbral
  más alto deja huecos en las ventanas invernales, que es cuando más nubosidad hay.
- **Se linkea por índice de imagen** con la colección de Sentinel-2, no por fecha.

## Satellite Embeddings de AlphaEarth — `GOOGLE/SATELLITE_EMBEDDING`

Producto de Google DeepMind: **64 bandas a 10 m** que codifican un año entero de observaciones
multi-sensor en un vector por píxel. La promesa es reemplazar el feature engineering manual.

- **Granularidad temporal: anual, por año calendario.** Ver la nota de abajo — es la limitación más
  importante de este dataset para el proyecto.
- **Escala:** los vectores vienen normalizados y no requieren estandarización adicional (a diferencia
  de las features clásicas, que sí se estandarizan antes del kNN).
- **Cobertura:** global, desde 2017.
- **Licencia:** verificar la ficha del dataset en el catálogo de Earth Engine antes de publicar —
  `PENDIENTE`.

### ⚠️ El desfase año calendario vs campaña agrícola

La campaña agrícola argentina va del **1 de julio al 30 de junio**. Los embeddings están indexados
por **año calendario**. Ningún embedding anual cubre una campaña:

```
campaña 2024/25   ├──────────────────────────────────────────┤
                  jul 2024        dic          ene        jun 2025
                     │ pico trigo  │            │ pico soja  │
                     │  sep-oct    │            │  ene-feb   │
embedding 2024  ├────────────────────┤
embedding 2025                       ├──────────────────────────────────┤
```

El pico del trigo cae en un año calendario y el de la soja en el otro. Por eso la configuración
principal **concatena los dos años que solapan la campaña** (128 features), y se reporta una ablación
con un solo año para cuantificar el costo. Las features clásicas no tienen este problema: se recortan
a la ventana exacta.

Esto es una desventaja estructural de los embeddings en agricultura de secano del hemisferio sur, y
está declarada como tal en [`../docs/METODOLOGIA.md → 7.1`](../docs/METODOLOGIA.md#7-limitaciones-declaradas).

## Mapa Nacional de Cultivos — INTA / GeoINTA

Capa nacional de cobertura agrícola por campaña, producida por el INTA (Programa Nacional de
Agricultura; equipo de de Abelleyra, Banchero, Verón y colaboradores).

- **Rol en este proyecto: capa de referencia y base del muestreo estratificado.** No es verdad de
  campo — es a su vez el producto de un clasificador, con su propio error. Contra ella se mide
  **acuerdo**, nunca *accuracy*. Ver
  [`../docs/METODOLOGIA.md → 1`](../docs/METODOLOGIA.md#1-el-mapa-nacional-de-cultivos-es-referencia-no-verdad-de-campo).
- **Cómo se obtiene:** el INTA publica cada campaña en Zenodo. La 2024/25 es el record
  [`10.5281/zenodo.17652712`](https://zenodo.org/records/17652712): dos GeoTIFF nacionales
  (`MNC_inv24.tif` invierno, `MNC_ver25.tif` verano, ~370 MB en total) más los `.qml` con los
  códigos de clase y el informe PDF. Los `.tif` viven **fuera del repo** (ruta en `MNC_DIR`) y se
  leen localmente con rasterio — no se suben a Earth Engine: solo los puntos muestreados viajan a EE.
- **Ojo: son DOS mapas por campaña** (invierno y verano, desde la 2023/24). La leyenda propia se
  deriva **cruzando ambos por píxel**; las reglas del cruce viven en `leyenda.json → mapeo_mnc` y
  se implementan en `referencia.py`. Lo que no matchea ninguna regla queda excluido del muestreo.
- **Verificar antes de arrancar:** que la campaña objetivo esté publicada. Se publica con retraso
  respecto del cierre de campaña. Si 2024/25 no está, se usa la última disponible — **el año es un
  parámetro del pipeline, no una constante**.
- **Accuracy que reporta el propio equipo** para la campaña usada: `PENDIENTE`. Está en el informe
  PDF del record de Zenodo; citarlo textual, no estimarlo. Es el techo implícito del acuerdo.
- **Licencia y atribución:** CC-BY-4.0. Citar: de Abelleyra et al., *Mapa Nacional de Cultivos
  campaña 2024/2025*, INTA. DOI `10.5281/zenodo.17652712`.

## Límites departamentales — IGN

Geometrías del departamento Río Cuarto (Córdoba) y del partido de Pergamino (Buenos Aires), del
Instituto Geográfico Nacional.

- Viven en `zonas.geojson`, **única fuente de verdad** de las geometrías. Ningún otro archivo define
  un límite.
- Se simplifican a una tolerancia que no altere el área a escala de 10 m, para no engordar el
  frontend.

## Estimaciones Agrícolas — MAGyP

Superficie sembrada y cosechada por departamento y campaña. Se usa solo como **contraste externo**
de la superficie estimada (ver [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md#superficie-sembrada-estimada)),
nunca como entrada del modelo.

---

## Qué vive en este directorio

| Archivo | Qué es | ¿Va a git? |
|---|---|---|
| `zonas.geojson` | Límites de las dos zonas. Única fuente de verdad | ✅ |
| `leyenda.json` | Clases, códigos, colores y mapeo desde el MNC | ✅ |
| `muestras/*.csv` | Tablas de muestreo. Permiten reproducir los números sin volver a muestrear | ✅ |
| `metrics.json` | Resultados que consume el frontend. Lo escribe `02_benchmark.py` | ✅ |
| `*.tif`, `tiles/` | Rasters exportados y tiles | ❌ Van al bucket de GCS |
| Key del service account | Credencial de Earth Engine | ❌ **Nunca.** Vive fuera del repo, ruta en `GEE_KEY_PATH` |

Las muestras se versionan a propósito: sin ellas el benchmark no es reproducible, y con ellas
cualquiera regenera los números exactos con un `make benchmark`.

**Regla de reproducibilidad:** cualquier archivo de este directorio que consuma el frontend o los
docs se regenera con un comando. Si hace falta editarlo a mano, el bug está en el script.
