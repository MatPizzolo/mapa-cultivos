# SPEC — Mapa de Cultivos con IA

Decisiones técnicas, pipeline y contratos. El **por qué** de las decisiones de método está en
[`METODOLOGIA.md`](METODOLOGIA.md); acá está el **qué** y el **cómo**.

---

## 1. Alcance y no-alcance

**Dentro:**

- Clasificación supervisada de cultivos a nivel de píxel, 10 m, sobre dos departamentos.
- Dos juegos de features × dos clasificadores = cuatro modelos comparados.
- Campaña **2024/25** clasificada y validada; campaña **2025/26** clasificada y publicada
  explícitamente como inferencia sin validar.
- Visor web con cortina comparativa, inspector de píxel y panel de métricas.
- Modo explorar: clasificación en vivo de un polígono dibujado.

**Fuera, y no se discute durante esta ventana de trabajo:**

- Más departamentos o cobertura provincial.
- Series multi-campaña, detección de cambio o rotaciones. Eso es el Nivel 4.
- Estimación de rinde. Eso es el Nivel 5 (RindeCast).
- Segmentación de lotes o clasificación a nivel objeto. Se clasifica píxel a píxel.
- Redes neuronales propias. El aporte del proyecto es el diseño experimental, no la arquitectura.
- Reentrenamiento desde la interfaz. Los modelos se entrenan offline.

## 2. Leyenda de clases

Seis clases, compartidas por las dos zonas para que las matrices sean comparables. Viven en
`data/leyenda.json`, que es la única fuente de verdad de códigos, nombres y colores.

| Código | Clase | Color | Notas |
|---|---|---|---|
| `1` | soja | `#4C9F70` | Soja de primera. La clase mayoritaria en las dos zonas |
| `2` | maíz | `#E8B33A` | Incluye maíz tardío, que desplaza el pico ~2 meses |
| `3` | trigo/soja 2ª | `#7B5EA7` | Doble cultivo como **una sola clase** — ver abajo |
| `4` | maní | `#D95F3B` | Solo presente en Río Cuarto |
| `5` | pastura/verdeo | `#3E8E8C` | Pasturas perennes y verdeos de invierno |
| `0` | no agrícola | `#9A9A93` | Urbano, agua, monte, caminos, suelo permanente |

**Por qué `trigo/soja 2ª` es una sola clase.** En la pampa el trigo casi siempre lleva soja de
segunda detrás en la misma campaña. Separar "trigo" de "soja de segunda" sería asignar dos etiquetas
a lo que en el píxel es una única secuencia anual con dos picos. La clase se define por esa
secuencia, y eso la conecta directo con la detección de doble cultivo del
[Nivel 2](../../monitoring/README.md).

**La clase `maní` en Pergamino.** No existe. No se elimina de la leyenda —eso rompería la
comparabilidad— sino que se reporta con soporte cero y se excluye del promedio macro de F1 de esa
zona. La matriz de Pergamino conserva la fila y la columna vacías, explícitamente rotuladas. Nunca
se promedia una clase sin soporte como si fuera un cero.

**Requisito de la paleta:** tiene que ser distinguible bajo deuteranopia y protanopia. Los valores
de arriba son la propuesta inicial y **deben pasar por un simulador antes de deployar**; el par
riesgoso es `soja` contra `maní`. Si no pasan, se ajusta la luminancia antes que el matiz.

## 3. Pipeline

```
data/zonas.geojson  ─┐
                     ├─→ referencia.py ──→ capa MNC remapeada a la leyenda
Mapa Nacional (INTA) ┘        │
                              ▼
                        muestras.py ──→ data/muestras/{zona}_{campania}.csv
                              │          (estratificado · bordes erosionados ·
                              │           bloques espaciales · semilla fija)
                              ▼
             ┌────────────────┴────────────────┐
             ▼                                 ▼
     features.clasicas()              features.embeddings()
     S2 + índices por ventana         AlphaEarth, 64 × 2 años
             └────────────────┬────────────────┘
                              ▼
                        clasificar.py ──→ 4 modelos (RF | kNN) × (clásicas | embeddings)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        evaluar.py                      exportar.py
   tabla de validación → sklearn      mapa clasificado → GeoTIFF
   data/metrics.json                  scripts/04_tiles.py → tiles XYZ → GCS
   docs/BENCHMARK.md
```

**Ventana de campaña.** La campaña `YYYY/YY+1` va del **1 de julio de `YYYY` al 30 de junio de
`YYYY+1`**. Todo filtrado de Sentinel-2 usa ese rango exacto. La constante vive en `zonas.py` y no se
duplica en ningún otro lado.

**Enmascarado de nubes.** Cloud Score+, banda `cs`, se descarta todo píxel por debajo de **0.60** —
mismo umbral que el [Monitor NDVI](../../monitoring/README.md), deliberadamente, para que los dos
proyectos sean comparables entre sí.

## 4. Los dos juegos de features

### 4.1 Clásicas — `features.clasicas()`

La campaña se parte en **seis ventanas fenológicas** y de cada una se toma la mediana de las
imágenes válidas:

| Ventana | Meses | Qué separa |
|---|---|---|
| W1 | jul – ago | Emergencia y macollaje de trigo contra barbecho |
| W2 | sep – oct | Pico del trigo. Es la ventana que aísla el doble cultivo |
| W3 | nov – dic | Maíz temprano en crecimiento, siembra de soja y maní |
| W4 | ene – feb | Pico de soja de primera y de maní; maíz ya senescente |
| W5 | mar – abr | Pico de soja de segunda, cosecha de maíz |
| W6 | may – jun | Rastrojo y cobertura invernal |

De cada ventana se extraen:

- **10 bandas** de reflectancia: `B2 B3 B4 B5 B6 B7 B8 B8A B11 B12`
- **4 índices**: NDVI `(B8−B4)/(B8+B4)`, EVI, NDMI `(B8−B11)/(B8+B11)`, NDRE `(B8A−B5)/(B8A+B5)`

Más **5 estadísticos de campaña completa** sobre la serie de NDVI: máximo, mínimo, amplitud,
desvío estándar y **día del año del máximo**. El último es de los más discriminativos: es lo que
separa maíz temprano de soja tardía sin mirar la magnitud.

Total: `6 × 14 + 5 = 89` features.

### 4.2 Embeddings — `features.embeddings()`

`GOOGLE/SATELLITE_EMBEDDING`: 64 bandas a 10 m, un vector por píxel por **año calendario**.

Una campaña cruza dos años calendario, y ninguno de los dos la cubre solo: el pico del trigo
(sep-oct 2024) cae en un año y el pico de soja (ene-feb 2025) en el otro. Entonces la configuración
principal **concatena los dos años que solapan la campaña**:

- Campaña 2024/25 → embeddings de 2024 **+** 2025 = **128 features**
- Campaña 2025/26 → embeddings de 2025 **+** 2026 = 128 features

Se reporta además una **ablación con un solo año** (el segundo, el del verano) para medir cuánto
cuesta el desfase. Esa ablación *es* uno de los resultados publicables: cuantifica una limitación
concreta del dataset para agricultura de secano en el hemisferio sur.

Con 89 vs 128 features los dos juegos quedan en un orden de magnitud comparable, así que la
diferencia de accuracy no se explica por dimensionalidad.

## 5. Los cuatro modelos

|  | Random Forest | kNN |
|---|---|---|
| **Clásicas** (89) | A | B |
| **Embeddings** (128) | C | D |

```python
# clasificar.py — un solo lugar, se itera. No se copia y pega cuatro veces.
RF  = ee.Classifier.smileRandomForest(
    numberOfTrees=300, minLeafPopulation=5, bagFraction=0.5, seed=SEED)
KNN = ee.Classifier.smileKNN(k=5, metric="EUCLIDEAN")
```

`SEED = 42`, definido en `settings.py`, usado en muestreo y en el RF.

**Estandarización, y por qué no es simétrica.** kNN sobre distancia euclídea es sensible a la escala:
las features clásicas mezclan reflectancias, índices en `[-1, 1]` y un día del año en `[1, 365]`, así
que se **estandarizan a z-score con media y desvío calculados solo sobre el set de entrenamiento**
antes de B. Los embeddings de AlphaEarth ya vienen en una escala homogénea y no se tocan. Random
Forest es invariante a escala monótona y no se estandariza en ningún caso.

Esta asimetría es una decisión, no un descuido, y va dicha en `BENCHMARK.md`: sin ella la celda B
pierde por una razón que no tiene nada que ver con las features.

## 6. Contrato de la API

FastAPI, mínimo. Todo lo que se puede servir estático se sirve estático.

| Método | Ruta | Qué devuelve |
|---|---|---|
| `GET` | `/health` | `{"status": "ok", "ee": true \| false}` — `ee` es el resultado de un ping barato a Earth Engine. Que dé `false` **no** degrada la app: solo el modo explorar |
| `GET` | `/metrics` | El contenido de `data/metrics.json` tal cual |
| `GET` | `/leyenda` | El contenido de `data/leyenda.json` tal cual |
| `POST` | `/clasificar` | Modo explorar. Ver abajo |

```jsonc
// POST /clasificar — request
{
  "geometry": { "type": "Polygon", "coordinates": [[[-64.3, -33.1], "..."]] },
  "campania": "2024-25",
  "modelo": "embeddings-rf"        // una de las 4 celdas
}

// response
{
  "clases": [
    { "codigo": 1, "clase": "soja", "ha": 0.0, "pct": 0.0 }
  ],
  "area_total_ha": 0.0,
  "advertencia": "Clasificación en vivo, no validada."
}
```

Límites de `/clasificar`: polígono de **hasta 5.000 ha**, dentro de Argentina, timeout de 25 s. Si
Earth Engine falla o timeoutea devuelve `503` con un mensaje en español; el frontend lo muestra
como aviso y **no rompe el resto de la vista**.

## 7. Esquema de `data/metrics.json`

Lo consume el frontend, así que es contrato. Lo escribe `scripts/02_benchmark.py` y **no se edita a
mano nunca**.

```jsonc
{
  "generado": "2026-08-06T21:14:00Z",
  "semilla": 42,
  "zonas": {
    "rio-cuarto": {
      "campania_validada": "2024-25",
      "muestras": { "entrenamiento": 0, "validacion_mnc": 0, "validacion_independiente": 0 },
      "modelos": {
        "clasicas-rf": {
          "acuerdo_mnc": { "overall": null, "kappa": null },
          "accuracy_independiente": { "overall": null, "ic95": [null, null] },
          "por_clase": [
            { "codigo": 1, "clase": "soja", "f1": null,
              "producer": null, "user": null, "soporte": 0 }
          ],
          "matriz_confusion": { "clases": [0,1,2,3,4,5], "filas": [] }
        }
        // clasicas-knn, embeddings-rf, embeddings-knn
      },
      "ablacion_embeddings_un_anio": { "overall": null }
    }
    // pergamino
  }
}
```

`null` significa "todavía no corrió". El frontend muestra `—` para `null`, nunca un cero.

## 8. Diseño del frontend

Una sola pantalla, sin rutas.

- **Mapa** — Leaflet. Dos capas de tiles superpuestas con un divisor arrastrable
  (`leaflet-side-by-side`). Izquierda: modelo clásico. Derecha: embeddings. El divisor arranca al
  medio y en mobile se arrastra con el dedo.
- **Controles** — selector de zona, selector de campaña, selector de qué par de modelos comparar.
  Todo en la barra inferior, alcanzable con el pulgar.
- **Rótulo de campaña sin validar** — al elegir 2025/26 aparece una banda persistente:
  *"Campaña 2025/26 — inferencia sin validar. No hay capa del INTA publicada para contrastar."*
  Persistente, no un toast que se va. No es negociable ni recortable.
- **Inspector de píxel** — al tocar el mapa, una ficha con: clase según cada modelo, clase según el
  MNC, y coordenadas. Cuando los modelos difieren, la ficha lo señala — el desacuerdo es el
  contenido, no un error.
- **Panel de métricas** — colapsado por defecto en mobile. Al abrirlo, la tabla 2×2 y el F1 por
  clase, leídos de `/metrics`. Cada número indica contra qué se midió: *acuerdo con MNC* o
  *accuracy independiente*. Nunca un número sin esa etiqueta.
- **Leyenda** — siempre visible, de `/leyenda`. Con patrón además del color, para que no dependa
  únicamente del matiz.

## 9. Deploy

- **Cloud Run**, misma región que el proyecto de Earth Engine. **`min-instances = 1` desde el
  viernes 7 hasta el 14 de agosto**: un cold start de varios segundos arruina la demo en el stand.
  Se baja a 0 después del evento.
- **Tiles** en un bucket de GCS público, `Cache-Control: public, max-age=31536000, immutable`, con
  el nombre de la corrida en la ruta para invalidar por versión en vez de por purga:
  `tiles/{corrida}/{zona}/{campania}/{modelo}/{z}/{x}/{y}.png`
- **Zooms 9 a 13.** Más abajo no se distingue nada; más arriba el peso se dispara sin agregar
  información — el dato original es de 10 m.
- **Presupuesto de peso:** ~10–20 MB por tileset (PNG paletizado de 6 colores comprime muy bien),
  ocho tilesets (2 zonas × 2 campañas × 2 modelos) → orden de 100 MB en el bucket. El **usuario**
  descarga solo los tiles de su viewport: la carga inicial tiene que quedar bajo los 300 KB sin
  contar tiles, y bajo ~1 MB contándolos a zoom de entrada.
- **CORS** habilitado en el bucket para el dominio del visor.

## 10. Cronograma

Hoy es **lunes 3 de agosto de 2026**. El evento es el 12-13.

| Fecha | Hito |
|---|---|
| **lun 3** | Docs y scaffolding del repo |
| **mar 4** | Zonas, capa del INTA, leyenda y muestreo. **El tramo más riesgoso** — es todo trabajo de datos y de él depende el resto |
| **mié 5** | Los dos juegos de features; primer RF corriendo de punta a punta |
| **jue 6** | Las cuatro celdas + métricas + `BENCHMARK.md` escrito. Los exports del mapa se lanzan a la noche |
| **vie 7** | Tiles y frontend con cortina. **La URL tiene que quedar viva hoy** para poder cargarla en `../portfolio/src/data/projects.ts` |
| **sáb 8** | Deploy en Cloud Run, `min-instances=1`, verificación en celular real con Slow 4G. Hoy se congela la URL del portfolio |
| **dom 9** | Se imprime el QR |
| **lun 10 – mar 11** | Capas 2 a 4, en ese orden, con lo que haya sobrado. Margen |
| **mié 12-13** | Evento |

**La restricción dura no es el evento, es el viernes 7.** El contenido del portfolio se puede editar
después de imprimir el QR, así que un `demoUrl` cargado tarde todavía llega — pero la URL en sí tiene
que existir antes de que el sábado 8 se congele el deploy del portfolio.

### Piso y orden de recorte

Decidido de antemano para no improvisarlo el día 10:

| Capa | Qué incluye | Cae si… |
|---|---|---|
| **Piso** | Río Cuarto · 24/25 · las 4 celdas · cortina + inspector + métricas | Nunca. Sin esto no hay proyecto que mostrar |
| **Capa 2** | Pergamino con el mismo pipeline | El etiquetado de muestras se estira |
| **Capa 3** | Campaña 25/26 sin validar | Falta tiempo de export y tiles |
| **Capa 4** | Modo explorar en vivo | Primera en caer |

## 11. Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| La capa del MNC 2024/25 no está publicada todavía | Media | El año es un **parámetro**, no una constante. Se cae a la última campaña publicada y se corren todos los docs con ese año. Verificar en GeoINTA el **martes 4 a primera hora**, antes de escribir nada de muestreo |
| El muestreo da clases muy desbalanceadas — sobre todo maní | Alta | Mínimo por clase en el muestreo estratificado y reporte explícito de soporte. Si maní no llega al mínimo, se reporta como clase de bajo soporte en vez de inflarla artificialmente |
| Los exports de GEE tardan más de lo previsto | Alta | Lanzarlos el **jueves a la noche**, no el viernes. Son la única parte del pipeline cuyo tiempo no se controla |
| Pergamino no llega | Media | Es la capa 2. El piso es Río Cuarto solo y el README ya lo dice |
| Los 200 puntos de validación independiente no se completan | Alta | Es trabajo manual de Mateo. Con menos de 100 puntos el intervalo de confianza se ensancha tanto que la métrica deja de discriminar: en ese caso se reporta **solo el acuerdo con el MNC**, diciendo explícitamente que falta la validación independiente. Nunca se llama accuracy a lo que no lo es |
| Cold start de Cloud Run en el stand | Media | `min-instances = 1` durante la ventana del evento |
| Cuota de Earth Engine agotada por el modo explorar | Baja | El modo explorar es la capa 4 y tiene límite de área y timeout. Si la cuota se agota, se apaga el endpoint y la app sigue entera |
