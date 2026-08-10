# Visor: explicación en capas + modo Desacuerdos + fichas 2×2 — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sumar al visor la explicación no técnica en capas, el modo "Desacuerdos" con tour de casos, y las fichas 2×2 del benchmark — según `docs/superpowers/specs/2026-08-10-visor-explicacion-desacuerdos-design.md`.

**Architecture:** Los datos nuevos (tiles de desacuerdo, % por zona) se generan offline de los GeoTIFFs ya exportados y se sirven como estáticos (bucket + `data/desacuerdo.json`). El frontend sigue vanilla: nuevas secciones en `app.js`/`index.html`/`styles.css` sobre los patrones existentes (hojas inferiores, chips, capas invisibles para el inspector).

**Tech Stack:** Python 3.12 + rasterio/numpy (script 05), FastAPI (un endpoint estático nuevo), Leaflet + JS plano.

## Global Constraints

- **Cero Earth Engine** (cuota restringida) — todo sale de los `.tif` locales en el scratchpad o de archivos ya publicados.
- Carga inicial **< 300 KB gzip** sin tiles; re-medir al final.
- **Strings visibles en rioplatense** (voseo); código y comentarios en inglés.
- Sin frameworks ni librerías nuevas de frontend.
- No se tocan `data/metrics.json`, `docs/BENCHMARK.md` ni el pipeline del benchmark.
- **El repo no está bajo git**: los pasos de commit se reemplazan por pasos de verificación. (Sugerencia pendiente para Mateo: `git init` + primer commit al cerrar esto.)
- Identidad de modelos: teal `#0d9488` = clásicas, naranja `#c2410c` = AlphaEarth (par validado CVD). La topbar verde no cambia; la paleta de clases del mapa no cambia.
- Los GeoTIFFs de entrada están en `/private/tmp/claude-501/-Users-mateo-Documents-code-dev-agro-mapa-cultivos/868ffac6-dbf9-495d-a83b-40c0c9899873/scratchpad/exports/` con nombres `{zona}_{campania}_{modelo}.tif`.

---

### Task 1: Módulo `tiles.py` compartido (refactor del tiler)

`scripts/04_tiles.py` tiene `paleta()` y `tilear()` que el script 05 necesita con otra paleta. Se mueven a `src/mapa_cultivos/tiles.py` con paleta parametrizable.

**Files:**
- Create: `src/mapa_cultivos/tiles.py`
- Modify: `scripts/04_tiles.py` (borra `paleta`/`tilear` locales; importa del módulo)
- Test: `tests/test_tiles.py`

**Interfaces:**
- Produces: `tiles.paleta_leyenda() -> tuple[list[int], dict[int, int]]` (colores PIL 768 + mapa código→índice, desde `data/leyenda.json`), y `tiles.tilear(datos, transform, crs, destino: Path, partes: tuple[str, ...], colores: list[int], indice: dict[int, int], nodata: int = 255) -> int` — `partes` son los segmentos de ruta bajo `destino` (p.ej. `("2026-08-09a", "rio-cuarto", "2024-25", "mnc")`); devuelve tiles escritos. Zooms 9–13, PNG paletizado con transparencia en `nodata`.

- [ ] **Step 1: Test del contrato de paleta y de un tileo sintético**

```python
# tests/test_tiles.py
import numpy as np
import rasterio
from rasterio.transform import from_origin

from mapa_cultivos import tiles


def test_paleta_leyenda_cubre_las_seis_clases():
    colores, indice = tiles.paleta_leyenda()
    assert len(colores) == 768
    assert sorted(indice) == [0, 1, 2, 3, 4, 5]


def test_tilear_raster_sintetico(tmp_path):
    datos = np.full((256, 256), 255, dtype=np.uint8)
    datos[100:200, 100:200] = 1  # un cuadrado de "soja" cerca de Río Cuarto
    transform = from_origin(-64.4, -33.0, 0.001, 0.001)
    colores, indice = tiles.paleta_leyenda()
    n = tiles.tilear(
        datos, transform, rasterio.crs.CRS.from_epsg(4326),
        tmp_path, ("t", "z", "c", "m"), colores, indice,
    )
    assert n > 0
    assert any((tmp_path / "t" / "z" / "c" / "m").rglob("*.png"))
```

- [ ] **Step 2: Correr y ver que falla** — `uv run pytest tests/test_tiles.py -q` → FAIL (`No module named 'mapa_cultivos.tiles'`).

- [ ] **Step 3: Crear `src/mapa_cultivos/tiles.py`** moviendo `paleta()` (renombrada `paleta_leyenda`) y `tilear()` desde `scripts/04_tiles.py` tal cual, con dos cambios: la firma nueva (`partes` en vez de los cuatro args fijos `corrida/zona/campania/modelo`; `colores`/`indice`/`nodata` como parámetros en vez de leídos adentro), y `EXCLUIDO` reemplazado por el parámetro `nodata`. Constantes `ZOOM_MIN/ZOOM_MAX/TAM` van al módulo.

- [ ] **Step 4: Adaptar `scripts/04_tiles.py`** para importar `from mapa_cultivos import tiles` y llamar `tiles.tilear(..., partes=(args.corrida, zona, campania, modelo), *tiles.paleta_leyenda())` — ojo al orden: pasar `colores=` e `indice=` por nombre.

- [ ] **Step 5: Verificar** — `uv run pytest -q` todo verde, y humo del script real:
  `uv run python scripts/04_tiles.py --mnc --zona pergamino --corrida check && rm -rf tiles/check`
  Esperado: `pergamino/mnc: 322 tiles` (mismo número que la corrida original).

---

### Task 2: `scripts/05_desacuerdo.py` — cruce, %, tiles y `data/desacuerdo.json`

**Files:**
- Create: `scripts/05_desacuerdo.py`
- Create: `src/mapa_cultivos/desacuerdo.py`
- Test: `tests/test_desacuerdo.py`
- Modify: `data/.gitignore`-no; el JSON nuevo SÍ se versiona (regenerable con un comando, patrón `metrics.json`).

**Interfaces:**
- Consumes: `tiles.tilear(...)` de Task 1.
- Produces: `desacuerdo.cruzar(a: np.ndarray, b: np.ndarray, nodata: int = 255) -> np.ndarray` (uint8: `1` donde ambos válidos y distintos, `0` donde ambos válidos e iguales, `255` donde alguno es nodata) y `desacuerdo.porcentaje(cruce: np.ndarray) -> float` (desacuerdos / píxeles válidos, 0–1, `0.0` si no hay válidos). El script escribe `data/desacuerdo.json` con esquema `{"generado": iso, "corrida": str, "zonas": {"rio-cuarto": {"rf": 0.083, "knn": 0.091}, "pergamino": {...}}}` y tilesets `tiles/{corrida}/{zona}/{campania}/desacuerdo-{rf|knn}/`.

- [ ] **Step 1: Tests del cruce**

```python
# tests/test_desacuerdo.py
import numpy as np

from mapa_cultivos import desacuerdo


def test_cruzar_marca_solo_diferencias_validas():
    a = np.array([[1, 1, 255], [2, 3, 4]], dtype=np.uint8)
    b = np.array([[1, 2, 1], [255, 3, 5]], dtype=np.uint8)
    c = desacuerdo.cruzar(a, b)
    esperado = np.array([[0, 1, 255], [255, 0, 1]], dtype=np.uint8)
    assert (c == esperado).all()


def test_porcentaje_ignora_nodata():
    c = np.array([[0, 1, 255, 255]], dtype=np.uint8)
    assert desacuerdo.porcentaje(c) == 0.5


def test_porcentaje_sin_validos_es_cero():
    c = np.full((2, 2), 255, dtype=np.uint8)
    assert desacuerdo.porcentaje(c) == 0.0
```

- [ ] **Step 2: Correr y ver que falla** — `uv run pytest tests/test_desacuerdo.py -q` → FAIL.

- [ ] **Step 3: Implementar `src/mapa_cultivos/desacuerdo.py`**

```python
"""Where the two feature sets disagree — computed from the exported maps."""

import numpy as np

NODATA = 255


def cruzar(a: np.ndarray, b: np.ndarray, nodata: int = NODATA) -> np.ndarray:
    valido = (a != nodata) & (b != nodata)
    salida = np.full(a.shape, nodata, dtype=np.uint8)
    salida[valido] = (a[valido] != b[valido]).astype(np.uint8)
    return salida


def porcentaje(cruce: np.ndarray, nodata: int = NODATA) -> float:
    validos = cruce != nodata
    if not validos.any():
        return 0.0
    return float((cruce[validos] == 1).mean())
```

- [ ] **Step 4: Tests verdes** — `uv run pytest tests/test_desacuerdo.py -q` → 3 passed.

- [ ] **Step 5: Script `scripts/05_desacuerdo.py`** — argparse: `--exports-dir` (obligatorio), `--corrida` (obligatorio, usar `2026-08-09a`), `--campania` (default de settings). Por zona × clasificador: abre `{zona}_{campania}_clasicas-{clf}.tif` y `..._embeddings-{clf}.tif` con rasterio (validar shapes iguales, si no `SystemExit` con mensaje), `cruce = desacuerdo.cruzar(...)`, `pct = desacuerdo.porcentaje(cruce)`, tilea con paleta propia: `colores` con índice 1 = magenta (color final de Task 3), índice 0 **transparente también** (solo se pinta el desacuerdo: `indice = {1: 0}` y el 0 del cruce va a nodata antes de tilear: `cruce[cruce == 0] = 255`). Escribe `data/desacuerdo.json` (json.dumps indent 2 + newline) e imprime por zona/clf: `rio-cuarto rf: 8.3 % de desacuerdo, N tiles`.

- [ ] **Step 6: Verificación real** — correr con `--exports-dir` del scratchpad. Esperado: 4 tilesets nuevos bajo `tiles/2026-08-09a/`, `data/desacuerdo.json` con 4 números entre 0 y 1, y porcentajes plausibles (el benchmark dice ~5–9 % de desacuerdo global).

---

### Task 3: Color del desacuerdo validado + endpoint `/desacuerdo`

**Files:**
- Modify: `scripts/05_desacuerdo.py` (fijar el hex ganador como constante `COLOR_DESACUERDO`)
- Modify: `src/mapa_cultivos/api/main.py` (endpoint nuevo tras `/zonas`)
- Test: `tests/test_api.py` (agregar test)

**Interfaces:**
- Produces: `GET /desacuerdo` → contenido de `data/desacuerdo.json` tal cual. Frontend lo consume en Task 7.

- [ ] **Step 1: Validar el magenta contra sus vecinos reales** (el fondo en modo Desacuerdos queda desaturado, pero el magenta convive con la paleta de clases en la leyenda y el inspector):
  `node <dataviz>/scripts/validate_palette.js "#E91E8C,#4C9F70,#E8B33A,#7B5EA7,#D95F3B,#3E8E8C,#9A9A93" --mode light`
  Si el par magenta↔algún vecino falla el floor normal-vision o CVD sin encoding secundario, probar `#C2185B` y `#8E24AA`; fijar el ganador en `COLOR_DESACUERDO` y regenerar los tiles de Task 2 si cambió.

- [ ] **Step 2: Test del endpoint**

```python
def test_desacuerdo_contract():
    r = client.get("/desacuerdo")
    assert r.status_code == 200
    body = r.json()
    assert set(body["zonas"]) == {"rio-cuarto", "pergamino"}
    for z in body["zonas"].values():
        assert set(z) == {"rf", "knn"}
```

- [ ] **Step 3: FAIL, implementar, PASS** — en `main.py`:

```python
@app.get("/desacuerdo")
def desacuerdo() -> FileResponse:
    return FileResponse(DATA_DIR / "desacuerdo.json", media_type="application/json")
```

- [ ] **Step 4: Subir los tilesets nuevos al bucket** —
  `gcloud storage cp -r --cache-control="public, max-age=31536000, immutable" tiles/2026-08-09a/*/2024-25/desacuerdo-* ...` no preserva la estructura: usar `gcloud storage rsync -r tiles/2026-08-09a gs://monitor-cultivos-bucket/tiles/2026-08-09a` y verificar con `curl` un tile `desacuerdo-rf` → 200 + header immutable. (Si gcloud vuelve a crashear como con las descargas, subir con `cp -r` por zona.)

---

### Task 4: Identidad teal/naranja

**Files:**
- Modify: `frontend/styles.css` (`:root`: `--ocre: #8a5a1a` → `--naranja: #c2410c`; nueva `--teal: #0d9488`; `.etiqueta-izq` color → `var(--teal)`; `.etiqueta-der` → `var(--naranja)`; buscar TODO uso restante de `--ocre` y reemplazar)
- Modify: `frontend/app.js` solo si referencia los hex viejos (hoy no).

- [ ] **Step 1: Reemplazos** — `grep -n "ocre\|8a5a1a" frontend/styles.css` y reemplazar cada uso; agregar las dos variables nuevas.
- [ ] **Step 2: Verificar** — `grep -c "8a5a1a" frontend/styles.css` → 0, y visual en `make dev`: etiquetas "Clásico S2" teal / "AlphaEarth" naranja.

---

### Task 5: Fichas 2×2 + frase criolla en el panel de métricas

**Files:**
- Modify: `frontend/app.js` — `dibujarMetricas()` (insertar fichas antes de la tabla) + helper `fraseCriolla(zona)`
- Modify: `frontend/styles.css` — clases `.fichas-2x2`, `.ficha-modelo`

**Interfaces:**
- Consumes: `estado.metrics.zonas[z].modelos[m].acuerdo_mnc.{overall, ic95}` y `estado.metrics.zonas[z].comparaciones[]` (objetos `{a, b, delta_overall, p, significativo}`).

- [ ] **Step 1: CSS**

```css
.fichas-2x2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; }
.ficha-modelo { border: 1px solid var(--borde); border-radius: 10px; padding: 8px 10px; }
.ficha-modelo.clasicas { border-left: 4px solid var(--teal); }
.ficha-modelo.embeddings { border-left: 4px solid var(--naranja); }
.ficha-modelo .ficha-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: .04em; color: var(--gris-texto); }
.ficha-modelo .ficha-num { font-size: 1.45rem; font-weight: 800; }
.ficha-modelo .ficha-ic { font-size: 0.68rem; color: var(--gris-texto); }
```

- [ ] **Step 2: JS** — en `dibujarMetricas()`, antes de `const filas = ...`:

```js
const fichas = modelos.map(([clave, nombre]) => {
  const a = zona.modelos[clave].acuerdo_mnc;
  const ic = a.ic95 && a.ic95[0] != null ? `IC 95: ${fmtPct(a.ic95[0])}–${fmtPct(a.ic95[1])}` : '';
  const familia = clave.startsWith('clasicas') ? 'clasicas' : 'embeddings';
  return `<div class="ficha-modelo ${familia}">
    <div class="ficha-label">${nombre}</div>
    <div class="ficha-num">${fmtPct(a.overall)}</div>
    <div class="ficha-ic">${ic}</div></div>`;
}).join('');
```

y `fraseCriolla(zona)`: toma `comparaciones` con `a === 'clasicas-rf'`; si `overall` de ambos lados es null → `''`; si `significativo` →
`De cada 100 píxeles, ${Math.round(cl*100)} dicen lo mismo que el mapa del INTA con las features clásicas y ${Math.round(em*100)} con AlphaEarth — la diferencia es estadísticamente real (McNemar, p ${p < 0.001 ? '< 0,001' : '= ' + p.toFixed(3).replace('.', ',')}).`
si no → `...— y con esta muestra los dos enfoques no se distinguen (McNemar, p = …).`
Insertar `<div class="fichas-2x2">${fichas}</div><p class="nota-metrica">${fraseCriolla(zona)}</p>` arriba de la tabla en el template de `cont.innerHTML`.

- [ ] **Step 3: Verificar** — `make dev`, abrir Métricas en ambas zonas: 4 fichas con IC, frase con p correcto (RC: `< 0,001`; Pergamino: `= 0,027`), tabla intacta debajo. Cambiar `metrics.json` por una copia con nulls NO (no se toca) — probar null-path seteando `estado.metrics` desde consola del browser.

---

### Task 6: Explicación en capas (onboarding + labels + hoja «?»)

**Files:**
- Modify: `frontend/index.html` — (a) opciones del select clasificador; (b) botón `#btn-ayuda` en `.topbar` junto al `h1`; (c) sección `#panel-ayuda` gemela de `#panel-metricas`; (d) `#toast-clasificador` (div vacío, `role="status"`); (e) reemplazar `#hint` por `#onboarding` con 2 tarjetas.
- Modify: `frontend/app.js` — sección nueva "6. Explicación" con `mostrarOnboarding()`, `pasoOnboarding(n)`, toast en el change de clasificador; borrar `ocultarHint()` y sus llamadas (incluida la de `dividermove`, que pasa a avanzar el onboarding si está en paso 1).
- Modify: `frontend/styles.css` — `.onboarding-tarjeta`, `.toast-clf`, `#btn-ayuda`, backdrop.

- [ ] **Step 1: HTML** — opciones del select: `<option value="rf" selected>Comité de reglas (RF)</option>` / `<option value="knn">Por similitud (kNN)</option>` (y en CSS subir `.control:nth-child(3)` a `flex: 1`). Botón ayuda: `<button id="btn-ayuda" aria-expanded="false" aria-controls="panel-ayuda">?</button>`. Panel:

```html
<section id="panel-ayuda" aria-label="Cómo se hizo este mapa" hidden>
  <div class="panel-encabezado"><h2>Cómo se hizo este mapa</h2>
    <button id="ayuda-cerrar" class="cerrar" aria-label="Cerrar ayuda">×</button></div>
  <p><b>Dos maneras de mirar el satélite.</b> «Clásico S2»: seis fotos del ciclo del cultivo más
    índices de vigor, elegidos por agrónomos. «AlphaEarth»: el resumen automático del año entero
    que arma la IA de Google.</p>
  <p><b>Dos maneras de decidir.</b> Comité de reglas (RF): 300 reglas simples miran cada lote y
    votan — gana la mayoría. Por similitud (kNN): busca los 5 lotes conocidos más parecidos y
    copia su etiqueta.</p>
  <p><b>Contra qué se compara.</b> El Mapa Nacional de Cultivos del INTA — que también es un mapa
    hecho por computadora, con sus propios errores. Por eso acá hablamos de <b>acuerdo</b> entre
    mapas y no de precisión. La precisión real se mide aparte, contra puntos revisados a mano.</p>
  <p class="nota-metrica">Referencia: Mapa Nacional de Cultivos 2024/25, INTA (de Abelleyra et al.),
    CC-BY 4.0 · doi:10.5281/zenodo.17652712.</p>
  <!-- TODO(mateo): sumar link al repo cuando esté publicado -->
</section>
```

Onboarding (dentro de `.mapa-marco`, reemplaza `<p id="hint">…`):

```html
<div id="onboarding" class="onboarding-backdrop" hidden>
  <div class="onboarding-tarjeta" role="dialog" aria-label="Bienvenida">
    <p class="paso-num" id="onboarding-paso">1 de 2</p>
    <p id="onboarding-texto">Dos IA distintas clasificaron cada lote de esta zona.
      <b>Arrastrá la línea</b> y encontrá dónde no se ponen de acuerdo.</p>
    <div class="onboarding-acciones">
      <button id="onboarding-saltar" class="btn-secundario" type="button">Saltar</button>
      <button id="onboarding-sig" class="btn-primario" type="button">Siguiente →</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: CSS** — backdrop `position:absolute; inset:0; background:rgba(30,36,32,.35); z-index:1060; pointer-events:none;` y `.onboarding-tarjeta { pointer-events:auto; }` centrada arriba (`top:14%`), estilo `.tarjeta`. Toast: fijo abajo-centro del mapa, píldora oscura (`background:#2b2b24; color:#fff`), `transition: opacity .3s` respetando `prefers-reduced-motion` (ya hay media query global). `#btn-ayuda`: círculo blanco 32px, texto verde, en la esquina derecha del topbar (`position:absolute; top:8px; right:10px` con `.topbar { position:relative }`).

- [ ] **Step 3: JS** —

```js
const PASOS_ONBOARDING = [
  'Dos IA distintas clasificaron cada lote de esta zona. <b>Arrastrá la línea</b> y encontrá dónde no se ponen de acuerdo.',
  'Tocá cualquier lote para ver qué dijo cada una — y qué dice el mapa del INTA en ese mismo punto.',
];
const TOAST_CLF = {
  rf: 'RF: 300 reglas simples votan qué cultivo es — gana la mayoría',
  knn: 'kNN: busca los 5 lotes conocidos más parecidos y copia su etiqueta',
};
```

`mostrarOnboarding()`: si `localStorage.getItem('onboarding-visto')` → return; muestra paso 0; "Siguiente" pasa a paso 1 y se relabela "¡Listo!"; el segundo click (o "Saltar" en cualquier momento) oculta y setea el flag. El drag real de la cortina (el handler de `dividermove` existente) avanza del paso 0 al 1 automáticamente; un click en el mapa cierra el paso 1 (reusar `estado.mapa.once('click', …)`). Toast: en el listener de `sel-clasificador`, `mostrarToast(TOAST_CLF[estado.clasificador])` con `clearTimeout` + `setTimeout(4000)`. Hoja «?»: mismos 4 handlers que métricas (abrir/cerrar, aria-expanded), y al abrirla cerrar `#panel-metricas` si estaba abierto (y viceversa — una sola hoja a la vez).

- [ ] **Step 4: Verificar** — `make dev` con localStorage limpio: onboarding aparece, "Saltar" funciona, drag avanza el paso, no reaparece al recargar. Cambiar clasificador muestra el toast 4 s. La hoja «?» abre/cierra y muestra la atribución. `uv run pytest -q` sigue verde (test de `/` sigue encontrando "Mapa de Cultivos").

---

### Task 7: Modo «Comparar | Desacuerdos» + tour de casos

**Files:**
- Modify: `frontend/index.html` — segmented control en `.topbar` bajo el título: `<div class="seg" role="tablist">` con dos botones `#modo-comparar` / `#modo-desacuerdos` (`aria-pressed`); strip `#casos` (chips) + ficha `#ficha-caso` dentro de `.mapa-marco`; línea `#linea-desacuerdo` (texto fijo del modo).
- Modify: `frontend/app.js` — `estado.modo`, `estado.capaDesacuerdo`, `estado.desacuerdo` (fetch de `/desacuerdo` en `arrancar()`), branch en `actualizarCapas()`, `CASOS`, `mostrarCaso(i)`.
- Modify: `frontend/styles.css` — `.seg`, `.modo-desacuerdos .leaflet-pane-base { filter: saturate(.25) brightness(1.05) }` (ver pane abajo), chips de casos, ficha.

**Interfaces:**
- Consumes: `GET /desacuerdo` (Task 3), tilesets `desacuerdo-{rf|knn}` (Task 2), identidad de Task 4.
- Produces: `CASOS: Array<{zona, latlng: [lat,lng], zoom, titulo, texto}>` — los textos definitivos llegan en Task 8; acá se implementa con un único caso placeholder marcado `// TODO(task 8)` y el strip oculto si `CASOS.filter(zona).length === 0`.

- [ ] **Step 1: Pane para el mapa base** — en `arrancar()`, antes del tileLayer OSM: `estado.mapa.createPane('base'); estado.mapa.getPane('base').classList.add('leaflet-pane-base'); estado.mapa.getPane('base').style.zIndex = 150;` y el OSM layer con `{ pane: 'base', ... }`. Así el filtro CSS desatura solo el fondo, nunca los overlays.

- [ ] **Step 2: Branch de capas** — en `actualizarCapas()`, tras el reset actual (incluir `capaDesacuerdo` en el loop de remoción y `$('map').classList.toggle('modo-desacuerdos', estado.modo === 'desacuerdos')`):

```js
if (estado.modo === 'desacuerdos') {
  estado.capaIzq = L.tileLayer(urlTiles(`clasicas-${estado.clasificador}`), { ...opciones, opacity: 0 }).addTo(m);
  estado.capaDer = L.tileLayer(urlTiles(`embeddings-${estado.clasificador}`), { ...opciones, opacity: 0 }).addTo(m);
  estado.capaMnc = L.tileLayer(urlTiles('mnc'), { ...opciones, opacity: 0 }).addTo(m);
  estado.capaDesacuerdo = L.tileLayer(urlTiles(`desacuerdo-${estado.clasificador}`), { ...opciones, opacity: 0.9 }).addTo(m);
  estado.capaDesacuerdo.on('tileload', tilesCargaron);
  estado.capaDesacuerdo.on('tileerror', fallaTiles);
  const pct = estado.desacuerdo?.zonas?.[estado.zona]?.[estado.clasificador];
  $('linea-desacuerdo').textContent = pct == null
    ? 'En magenta, los píxeles donde los dos enfoques no coinciden.'
    : `En magenta, los píxeles donde los dos enfoques no coinciden (${(pct * 100).toFixed(1).replace('.', ',')} % del área).`;
  $('linea-desacuerdo').hidden = false;
  dibujarCasos();
} else { /* rama actual tal cual, + $('linea-desacuerdo').hidden = true; $('casos').hidden = true; $('ficha-caso').hidden = true; */ }
```

El inspector no cambia: lee `capaIzq/capaDer/capaMnc` que siguen cargadas invisibles.

- [ ] **Step 3: Segmented + casos JS** — listeners de los dos botones setean `estado.modo`, `aria-pressed`, y llaman `actualizarCapas()`. `dibujarCasos()`: filtra `CASOS` por zona; si hay, renderiza chips en `#casos` y lo muestra. `mostrarCaso(i)`: `estado.mapa.setView(caso.latlng, caso.zoom)`, llena `#ficha-caso` (título + texto + botón cerrar) y la muestra.

- [ ] **Step 4: Verificar** — `make dev`: alternar modos; en Desacuerdos el fondo queda gris suave, el magenta encima, la línea con % real, el inspector sigue mostrando las 3 filas al tocar; en Comparar todo queda como antes. `uv run pytest -q` verde.

---

### Task 8: Casos del tour — análisis, textos y aprobación de Mateo

**Files:**
- Create: `scripts/06_casos.py` (análisis exploratorio, se queda en el repo como evidencia)
- Modify: `frontend/app.js` (`CASOS` definitivo)

- [ ] **Step 1: Detectar candidatos** — `scripts/06_casos.py`: por zona, abre el cruce rf (recalculado con `desacuerdo.cruzar`), etiqueta componentes conexos de desacuerdo con `scipy.ndimage.label`, toma los 10 más grandes, y para cada uno reporta: centroide en lon/lat, hectáreas aproximadas, y qué clase dijo cada modelo (moda dentro del parche en cada raster). Imprime tabla ordenada.

- [ ] **Step 2: Elegir 3 y redactar** — elegir parches con historias distintas (prioridad: maní↔soja en RC; trigo/soja 2ª en Pergamino; el tercero, el contraste más claro que aparezca). Verificar cada centroide mirando los tiles publicados en el visor local. Redactar título + 2 frases por caso, estilo ficha de la maqueta C («El comité de reglas dice maní; AlphaEarth ve soja. La firma del maní se parece a la soja temprana y acá es donde el benchmark se decide.»).

- [ ] **Step 3: GATE — mostrar a Mateo** los 3 casos (coordenadas + capturas o links al visor + textos) y esperar su OK. Los textos no se fijan sin aprobación (spec §2).

- [ ] **Step 4: Fijar `CASOS`** en `app.js` con los aprobados y verificar los vuelos en el visor.

---

### Task 9: Peso, accesibilidad y deploy

- [ ] **Step 1: Suite y peso** — `uv run pytest -q` (todo verde) y el presupuesto:
  `cd frontend && for f in index.html styles.css app.js vendor/*.js vendor/*.css; do gzip -c "$f" | wc -c; done | awk '{s+=$1} END {print s/1024 " KB gzip"}'` → esperado < 70 KB (budget 300).
- [ ] **Step 2: Revisión manual 390 px** — DevTools iPhone SE + Slow 4G contra `make dev`: onboarding, hoja «?», modo Desacuerdos, tour, fichas 2×2, foco visible con Tab en todos los controles nuevos.
- [ ] **Step 3: Deploy** — `gcloud run deploy mapa-cultivos --source . --region southamerica-east1 --project monitor-cultivos --allow-unauthenticated --max-instances 2 --min-instances 1 --memory 512Mi --quiet` y smoke en prod: `/` 200, `/desacuerdo` 200, un tile `desacuerdo-rf` del bucket 200.
- [ ] **Step 4: Verificación final en prod** — recorrido completo en el celular real de Mateo (queda para Mateo; avisarle qué probar).

---

## Self-review

- **Cobertura del spec:** explicación en capas → Task 6; modo Desacuerdos + ficha → Tasks 2/3/7; tour → Task 8 (con gate); fichas 2×2 + frase → Task 5; teal/naranja → Task 4; color validado → Task 3 Step 1; % por zona servido → Task 3; errores de tiles en modo nuevo → Task 7 Step 2 (reusa `fallaTiles`); fuera de alcance respetado.
- **Placeholders:** el único deliberado es `CASOS` en Task 7 (resuelto por Task 8 con gate de aprobación — es un requisito del spec, no un hueco).
- **Consistencia de nombres:** `tiles.tilear/paleta_leyenda` (T1) usados en T2; `desacuerdo.cruzar/porcentaje` (T2) usados en T2/T8; `estado.capaDesacuerdo`, `dibujarCasos`, `mostrarCaso`, `TOAST_CLF`, `PASOS_ONBOARDING` definidos donde se usan; `/desacuerdo` (T3) consumido en T7.
