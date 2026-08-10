# Rediseño UI/UX del visor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved UI/UX redesign (spec: `docs/superpowers/specs/2026-08-09-ui-ux-visor-design.md`): layout C (controls in header, free map), "Campo moderno" identity, visible curtain handle, and the honest no-tiles state backed by a new `GET /zonas` endpoint.

**Architecture:** Pure-static frontend changes (`index.html`, `styles.css`, `app.js` — no build, no new deps) plus one FastAPI endpoint mirroring `/leyenda`. The no-tiles state is a small state machine in `app.js` driven by Leaflet `tileerror`/`tileload` events, with copy chosen from `metrics.generado`.

**Tech Stack:** HTML + vanilla JS + Leaflet 1.x + leaflet-side-by-side (vendored), FastAPI + pytest.

## Global Constraints

- No new dependencies, no webfonts, no frontend framework. `frontend/vendor/*` is never modified.
- Weight budget: styles.css + app.js + Leaflet < 300 KB transferred (comment at top of styles.css).
- User-visible strings in español rioplatense (voseo); code and comments in English.
- Class palette and patterns from `data/leyenda.json` unchanged; MNC metrics never labeled "accuracy".
- Contrast AA on all new chrome; `:focus-visible` ring on every interactive element; `prefers-reduced-motion` respected for new transitions.
- **No git in this project (user decision): all "Commit" steps are skipped.**

---

### Task 1: `GET /zonas` endpoint

**Files:**
- Modify: `src/mapa_cultivos/api/main.py` (add route next to `/leyenda`, line ~30)
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `GET /zonas` → the raw contents of `data/zonas.geojson` (FeatureCollection with 2 features whose `properties.zona` are `rio-cuarto` and `pergamino`). Task 3 consumes it via `fetch('/zonas')`.

- [x] **Step 1: Write the failing test** — append to `tests/test_api.py`:

```python
def test_zonas_contract():
    r = client.get("/zonas")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert {f["properties"]["zona"] for f in body["features"]} == {"rio-cuarto", "pergamino"}
```

- [x] **Step 2: Run it, expect FAIL** — `uv run pytest tests/test_api.py::test_zonas_contract -v` → 404.

- [x] **Step 3: Implement** — in `src/mapa_cultivos/api/main.py`, after the `/leyenda` route:

```python
@app.get("/zonas")
def zonas() -> FileResponse:
    return FileResponse(DATA_DIR / "zonas.geojson", media_type="application/geo+json")
```

- [x] **Step 4: Run the whole API suite, expect PASS** — `uv run pytest tests/test_api.py -v`.

---

### Task 2: Markup + identity (`index.html`, `styles.css`)

**Files:**
- Modify: `frontend/index.html` (full restructure)
- Modify: `frontend/styles.css` (full rewrite; keep the class-pattern rules verbatim)

**Interfaces:**
- Produces (element ids Task 3 depends on): `sel-zona`, `sel-campania`, `sel-clasificador`, `banda-sin-validar`, `banda-tiles`, `banda-tiles-texto`, `banda-tiles-reintentar`, `map`, `leyenda`, `leyenda-toggle`, `leyenda-items`, `btn-metricas`, `hint`, `inspector` (+ its inner ids unchanged), `tarjeta-tiles`, `tarjeta-tiles-texto`, `tarjeta-tiles-reintentar`, `tarjeta-tiles-cerrar`, `panel-metricas`, `metricas-cerrar`, `metricas-contenido`.
- CSS classes Task 3 toggles: `.hint.oculto`, `.marcador-pixel` (divIcon).

- [x] **Step 1: Rewrite `frontend/index.html`** body structure (head unchanged):
  - Header: `h1` + subtitle "Dos modelos miran el mismo lote — compará vos" + a `.controles` row with the three existing `<select>`s (same ids/options) each wrapped in `<label class="control"><span class="control-nombre">…</span>…</label>`.
  - Keep `#banda-sin-validar` as-is. Replace `#aviso-tiles` with `#banda-tiles` (span `#banda-tiles-texto` + button `#banda-tiles-reintentar` "Reintentar ↻").
  - Wrap the map in `<div class="mapa-marco">` containing: `#map`, curtain labels (`<span class="etiqueta-lado etiqueta-izq" aria-hidden="true">Clásico S2</span>`, mirror for "AlphaEarth"), `#leyenda-toggle` button ("▲ Clases", `aria-expanded` + `aria-controls="leyenda"`), `#leyenda` (now `hidden`-able), `#btn-metricas` (moved here from the removed bottom bar), `#hint`, `#inspector` (inner content unchanged), new `#tarjeta-tiles` card (`role="alert"`, `h2` "El mapa clasificado no cargó", `<p id="tarjeta-tiles-texto">`, actions row with `#tarjeta-tiles-reintentar` "Reintentar ↻" and `#tarjeta-tiles-cerrar` "Cerrar"), and `#panel-metricas` (unchanged content).
  - Delete `<nav class="barra-inferior">` entirely.

- [x] **Step 2: Rewrite `frontend/styles.css`** with the Campo moderno tokens and layout-C rules. Key blocks (complete values):

```css
:root {
  --tinta: #2b2b24; --fondo: #f6f3ea; --panel: #fff; --borde: #d8d5cd;
  --verde: #2f6c46; --ocre: #8a5a1a; --gris-texto: #555d56;
  --aviso-fondo: #7a4a12; --sombra: 0 2px 10px rgba(25,28,24,.2); --radio: 12px;
}
.topbar { background: var(--verde); color: #fff; padding: 8px 12px 10px; }
.controles { display: flex; gap: 6px; margin-top: 8px; }
.control select {
  appearance: none; font: inherit; font-size: .85rem; font-weight: 600;
  min-height: 40px; width: 100%; padding: 6px 26px 6px 12px;
  border: 1px solid rgba(255,255,255,.35); border-radius: 999px;
  background: rgba(255,255,255,.16) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5l5 5 5-5' stroke='%23fff' stroke-width='2' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right 10px center / 12px 8px;
  color: #fff;
}
.topbar :focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
.mapa-marco { flex: 1; min-height: 0; position: relative; display: flex; }
.etiqueta-lado { position: absolute; top: 10px; z-index: 1000; background: var(--panel);
  border-radius: 999px; padding: 4px 10px; font-size: .75rem; font-weight: 700; box-shadow: var(--sombra); }
.etiqueta-izq { left: 10px; color: var(--verde); }
.etiqueta-der { right: 10px; color: var(--ocre); }
.leaflet-top.leaflet-right { top: 44px; }            /* zoom control clears the label */
#leyenda-toggle { position: absolute; left: 10px; bottom: 12px; z-index: 1000; min-height: 44px;
  border: none; border-radius: 999px; padding: 10px 16px; font: inherit; font-size: .85rem;
  font-weight: 700; background: var(--panel); color: var(--tinta); box-shadow: var(--sombra); cursor: pointer; }
#btn-metricas { position: absolute; right: 10px; bottom: 12px; z-index: 1000; min-height: 44px;
  border: none; border-radius: 999px; padding: 10px 18px; font: inherit; font-size: .85rem;
  font-weight: 700; background: var(--verde); color: #fff; box-shadow: var(--sombra); cursor: pointer; }
#leyenda { position: absolute; left: 10px; bottom: 64px; z-index: 1000; /* panel styles as today */ }
.hint { position: absolute; top: 48px; left: 50%; transform: translateX(-50%); z-index: 1000;
  transition: opacity .3s, visibility .3s; /* pill styles as today */ }
.hint.oculto { opacity: 0; visibility: hidden; }
.tarjeta { position: absolute; left: 10px; right: 10px; bottom: 64px; width: auto; z-index: 1050;
  border-radius: var(--radio); /* rest as today */ }
.marcador-pixel { border-radius: 50%; border: 3px solid #fff;
  box-shadow: 0 0 0 2px var(--tinta), inset 0 0 0 2px var(--tinta); background: transparent; }
.reintentar-link { background: none; border: none; color: #fff; text-decoration: underline;
  font: inherit; font-weight: 700; cursor: pointer; }
.btn-primario { background: var(--verde); color: #fff; border: none; border-radius: 999px;
  min-height: 44px; padding: 10px 18px; font: inherit; font-weight: 700; cursor: pointer; }
.btn-secundario { background: var(--panel); color: var(--gris-texto); border: 1px solid var(--borde);
  border-radius: 999px; min-height: 44px; padding: 10px 16px; font: inherit; font-weight: 600; cursor: pointer; }
/* curtain */
.leaflet-sbs-divider { width: 3px; margin-left: -1.5px; background: #fff; box-shadow: 0 0 6px rgba(0,0,0,.45); }
.leaflet-sbs-range::-webkit-slider-thumb, .leaflet-sbs-range::-moz-range-thumb {
  height: 44px; width: 44px; border-radius: 22px; border: none; background-color: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,.35); background-size: 44px 44px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 44 44'%3E%3Cpath d='M19 22h-8m4-4l-4 4 4 4m10-4h8m-4-4l4 4-4 4' stroke='%232f6c46' stroke-width='2.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
}
```
  (Webkit and moz thumb rules must stay in **separate** rule blocks — a combined selector is dropped by both engines. Keep the five `.patron-*` rules, `.muestra-color`, `.chip`, `.desacuerdo`, `.coords`, `.cerrar`, metrics-panel and media-query blocks from today's file, restyled with the new tokens.)

- [x] **Step 3: Smoke-verify statically** — `uv run uvicorn mapa_cultivos.api.main:app --port 8765 &`; `curl -s localhost:8765/ | grep -c "tarjeta-tiles\|etiqueta-lado"` ≥ 2; page renders (JS still wired to old ids is fixed in Task 3 — expected console errors are OK at this checkpoint).

---

### Task 3: Behavior (`app.js`): zona layer, no-tiles state machine, ephemeral hint, collapsible legend, new marker

**Files:**
- Modify: `frontend/app.js`

**Interfaces:**
- Consumes: `GET /zonas` (Task 1); element ids/classes from Task 2.
- Produces: functions `dibujarZona(destacada)`, `fallaTiles()`, `tilesCargaron()`, `reintentarTiles()`, `ocultarHint()`, `mostrarLeyenda(abierta)`.

- [x] **Step 1: Extend startup** — add `/zonas` to the initial `Promise.all`; add to `estado`: `zonas: null, capaZona: null, algunTileCargado: false, avisoCerrado: false`. Add display names:

```js
const NOMBRES = { 'rio-cuarto': 'Río Cuarto', 'pergamino': 'Pergamino' };
```

- [x] **Step 2: Zone layer** — always-on thin border; dashed + soft fill while tiles are missing:

```js
function dibujarZona(destacada) {
  if (estado.capaZona) estado.capaZona.remove();
  const estilo = destacada
    ? { color: '#2f6c46', weight: 2, dashArray: '6 6', fillColor: '#2f6c46', fillOpacity: 0.08 }
    : { color: '#2f6c46', weight: 2, opacity: 0.7, fill: false };
  estado.capaZona = L.geoJSON(estado.zonas, {
    filter: (f) => f.properties.zona === estado.zona,
    style: estilo, interactive: false,
  }).addTo(estado.mapa);
}
```

- [x] **Step 3: No-tiles state machine** — replace the single `tileerror` handler in `actualizarCapas()`:

```js
estado.algunTileCargado = false;
estado.avisoCerrado = false;
$('tarjeta-tiles').hidden = true;
$('banda-tiles').hidden = true;
dibujarZona(false);
for (const capa of [estado.capaIzq, estado.capaDer]) {
  capa.on('tileload', tilesCargaron);
  capa.on('tileerror', fallaTiles);
}
```

```js
function textoFallaTiles() {
  // Honest copy per cause: pipeline never ran (dev) vs tiles unreachable (prod).
  if (estado.metrics.generado == null) {
    return 'El pipeline todavía no corrió: los mapas aparecen cuando se generen los tiles.';
  }
  return `La zona marcada es ${NOMBRES[estado.zona]}. Revisá la conexión y reintentá.`;
}

function fallaTiles() {
  if (estado.algunTileCargado) return;       // partial failure: keep the map, no card
  dibujarZona(true);
  if (estado.avisoCerrado) {
    $('banda-tiles-texto').textContent = textoFallaTiles();
    $('banda-tiles').hidden = false;
  } else {
    $('tarjeta-tiles-texto').textContent = textoFallaTiles();
    $('tarjeta-tiles').hidden = false;
  }
}

function tilesCargaron() {
  estado.algunTileCargado = true;
  dibujarZona(false);
  $('tarjeta-tiles').hidden = true;
  $('banda-tiles').hidden = true;
}

function reintentarTiles() { actualizarCapas(); }
```

  Wire in `conectarControles()`: `tarjeta-tiles-reintentar` and `banda-tiles-reintentar` → `reintentarTiles`; `tarjeta-tiles-cerrar` → set `estado.avisoCerrado = true`, hide card, show band with the same text.

- [x] **Step 4: Ephemeral hint** —

```js
function ocultarHint() { $('hint').classList.add('oculto'); }
```
  In `arrancar()`: `setTimeout(ocultarHint, 10000); estado.mapa.once('click', ocultarHint);` and after creating the curtain in `actualizarCapas()`: `estado.cortina.once('dividermove', ocultarHint);` (event exists: vendor line 129).

- [x] **Step 5: Collapsible legend** —

```js
function mostrarLeyenda(abierta) {
  $('leyenda').hidden = !abierta;
  $('leyenda-toggle').setAttribute('aria-expanded', String(abierta));
  $('leyenda-toggle').textContent = abierta ? '▼ Clases' : '▲ Clases';
}
```
  In `arrancar()`: open on first visit only — `mostrarLeyenda(!localStorage.getItem('leyenda-vista')); localStorage.setItem('leyenda-vista', '1');`. Toggle button click → `mostrarLeyenda($('leyenda').hidden)`.

- [x] **Step 6: New pixel marker** — replace the `L.circleMarker` in `inspeccionarPixel()`:

```js
estado.marcador = L.marker(evento.latlng, {
  icon: L.divIcon({ className: 'marcador-pixel', iconSize: [14, 14] }),
  interactive: false,
}).addTo(estado.mapa);
```

- [x] **Step 7: Verify end-to-end in dev** — with the server from Task 2 running: page loads with no console errors; no tiles present → dashed zone + card with dev copy; "Cerrar" → band; "Reintentar" re-creates layers; legend toggles; hint fades; `uv run pytest` all green.

---

### Task 4: Final verification pass

**Files:** none (verification only)

- [x] **Step 1: Weight budget** — `curl -so /dev/null -w '%{size_download}\n'` for `/`, `styles.css`, `app.js`, `vendor/leaflet.js`, `vendor/leaflet.css`; sum < 300 KB.
- [x] **Step 2: 390 px check** — open the page at 390×844 (o Slow 4G en DevTools si hay browser): header + chips sin scroll, cortina arrastrable desde el asa, etiquetas legibles, inspector anclado no tapa los chips.
- [x] **Step 3: Accessibility spot-check** — tab through: selects → leyenda-toggle → métricas → (tarjeta si visible); focus ring visible en header (blanco) y en superficie clara (verde); `prefers-reduced-motion` no anima el hint.
- [x] **Step 4: Honesty check** — ninguna string nueva usa "accuracy" para el MNC; copy dev vs prod correcto según `metrics.generado`.
