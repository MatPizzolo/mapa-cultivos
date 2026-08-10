/* Visor del benchmark: cortina comparativa, inspector de píxel y panel de métricas.
 * Vanilla JS a propósito — ver README "Stack". Sin build: lo que se lee es lo que corre.
 *
 * Estructura:
 *   1. Config de tiles          — de dónde salen los mapas clasificados
 *   2. Estado y arranque        — fetch de /leyenda y /metrics, init del mapa
 *   3. Capas y cortina          — leaflet-side-by-side, clásicas (izq) vs embeddings (der)
 *   4. Inspector de píxel       — lee el color del tile en canvas y lo mapea a clase
 *   5. Panel de métricas        — renderiza metrics.json; null → "—", nunca un cero
 *   6. Explicación              — onboarding de 2 pasos, toast de clasificador, hoja «?»
 *   7. Tour de casos            — chips de casos destacados en modo Desacuerdos
 */

'use strict';

// ---------- 1. Config de tiles ----------

// Tiles precomputados en GCS, cache inmutable, corrida versionada en la ruta
// (SPEC §9): {TILES_BASE}/{CORRIDA}/{zona}/{campania}/{modelo}/{z}/{x}/{y}.png
// Para desarrollo con tiles locales: TILES_BASE = '/tiles', CORRIDA = 'dev'.
const TILES_BASE = 'https://storage.googleapis.com/monitor-cultivos-bucket/tiles';
const CORRIDA = '2026-08-09a';

// El dato original es de 10 m: por debajo de z9 no se distingue nada y por
// encima de z13 el peso se dispara sin agregar información (SPEC §9).
const ZOOM_MIN = 9;
const ZOOM_MAX = 13;

// Centros de vista iniciales — solo encuadre, no son datos del proyecto.
const VISTAS = {
  'rio-cuarto': { centro: [-33.13, -64.35], zoom: 10 },
  'pergamino': { centro: [-33.89, -60.57], zoom: 11 },
};

// Display names for user-visible copy (the machine ids stay in VISTAS/selects).
const NOMBRES = { 'rio-cuarto': 'Río Cuarto', 'pergamino': 'Pergamino' };

// ---------- 2. Estado y arranque ----------

const $ = (id) => document.getElementById(id);

const estado = {
  zona: 'rio-cuarto',
  campania: '2024-25',
  clasificador: 'rf', // la cortina siempre compara filas: clásicas vs embeddings
  modo: 'comparar',    // 'comparar' | 'desacuerdos'
  leyenda: null,      // /leyenda
  metrics: null,      // /metrics
  zonas: null,        // /zonas — department outlines, drawn always, highlighted on failure
  desacuerdo: null,   // /desacuerdo
  mapa: null,
  capaIzq: null,      // clásicas
  capaDer: null,      // embeddings
  capaMnc: null,      // invisible: solo la lee el inspector
  capaDesacuerdo: null, // magenta: solo visible en modo Desacuerdos
  capaZona: null,
  cortina: null,
  cortinaX: null,     // last divider position; used to tell real drags from init events
  marcador: null,
  algunTileCargado: false, // any classified tile rendered this attempt
  avisoCerrado: false,     // user dismissed the no-tiles card → degrade to the band
};

async function arrancar() {
  const [leyenda, metrics, zonas, desacuerdo] = await Promise.all([
    fetch('/leyenda').then((r) => r.json()),
    fetch('/metrics').then((r) => r.json()),
    fetch('/zonas').then((r) => r.json()),
    fetch('/desacuerdo').then((r) => r.json()),
  ]);
  estado.leyenda = leyenda;
  estado.metrics = metrics;
  estado.zonas = zonas;
  estado.desacuerdo = desacuerdo;

  const vista = VISTAS[estado.zona];
  estado.mapa = L.map('map', {
    center: vista.centro,
    zoom: vista.zoom,
    minZoom: ZOOM_MIN,
    maxZoom: ZOOM_MAX,
    zoomControl: false,
  });
  L.control.zoom({ position: 'topright' }).addTo(estado.mapa);

  // Pane propio para el mapa base: así el filtro de desaturación del modo
  // Desacuerdos (styles.css) toca solo el fondo y nunca los overlays.
  estado.mapa.createPane('base');
  estado.mapa.getPane('base').classList.add('leaflet-pane-base');
  estado.mapa.getPane('base').style.zIndex = 150;

  // Mapa base liviano, solo para orientarse: los tiles clasificados van encima.
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    maxZoom: ZOOM_MAX,
    pane: 'base',
  }).addTo(estado.mapa);

  dibujarLeyenda();
  // Legend opens expanded only on the first visit; later visits start collapsed.
  mostrarLeyenda(!localStorage.getItem('leyenda-vista'));
  localStorage.setItem('leyenda-vista', '1');

  actualizarCapas();
  conectarControles();

  estado.mapa.on('click', inspeccionarPixel);

  mostrarOnboarding();
}

function mostrarLeyenda(abierta) {
  $('leyenda').hidden = !abierta;
  $('leyenda-toggle').setAttribute('aria-expanded', String(abierta));
  $('leyenda-toggle').textContent = abierta ? '▼ Clases' : '▲ Clases';
}

function conectarControles() {
  $('modo-comparar').addEventListener('click', () => cambiarModo('comparar'));
  $('modo-desacuerdos').addEventListener('click', () => cambiarModo('desacuerdos'));

  $('sel-zona').addEventListener('change', (e) => {
    estado.zona = e.target.value;
    const vista = VISTAS[estado.zona];
    estado.mapa.setView(vista.centro, vista.zoom);
    actualizarCapas();
    dibujarMetricas();
  });

  $('sel-campania').addEventListener('change', (e) => {
    estado.campania = e.target.value;
    // Banda persistente, no un toast: no es negociable ni recortable (SPEC §8).
    $('banda-sin-validar').hidden = estado.campania !== '2025-26';
    actualizarCapas();
  });

  $('sel-clasificador').addEventListener('change', (e) => {
    estado.clasificador = e.target.value;
    actualizarCapas();
    mostrarToast(TOAST_CLF[estado.clasificador]);
  });

  $('btn-metricas').addEventListener('click', () => {
    const panel = $('panel-metricas');
    const abrir = panel.hidden;
    if (abrir) cerrarAyuda();
    panel.hidden = !abrir;
    $('btn-metricas').setAttribute('aria-expanded', String(abrir));
    if (abrir) dibujarMetricas();
  });
  $('metricas-cerrar').addEventListener('click', () => {
    $('panel-metricas').hidden = true;
    $('btn-metricas').setAttribute('aria-expanded', 'false');
  });

  $('btn-ayuda').addEventListener('click', () => {
    const panel = $('panel-ayuda');
    const abrir = panel.hidden;
    if (abrir) {
      $('panel-metricas').hidden = true;
      $('btn-metricas').setAttribute('aria-expanded', 'false');
    }
    panel.hidden = !abrir;
    $('btn-ayuda').setAttribute('aria-expanded', String(abrir));
  });
  $('ayuda-cerrar').addEventListener('click', cerrarAyuda);

  $('onboarding-saltar').addEventListener('click', cerrarOnboarding);
  $('onboarding-sig').addEventListener('click', () => pasoOnboarding(pasoActualOnboarding + 1));

  $('inspector-cerrar').addEventListener('click', cerrarInspector);
  $('ficha-caso-cerrar').addEventListener('click', cerrarFicha);

  $('leyenda-toggle').addEventListener('click', () => mostrarLeyenda($('leyenda').hidden));

  $('tarjeta-tiles-reintentar').addEventListener('click', reintentarTiles);
  $('banda-tiles-reintentar').addEventListener('click', reintentarTiles);
  $('tarjeta-tiles-cerrar').addEventListener('click', () => {
    estado.avisoCerrado = true;
    $('tarjeta-tiles').hidden = true;
    $('banda-tiles-texto').textContent = textoFallaTiles(true);
    $('banda-tiles').hidden = false;
  });
}

// ---------- 3. Capas y cortina ----------

function urlTiles(modelo) {
  return `${TILES_BASE}/${CORRIDA}/${estado.zona}/${estado.campania}/${modelo}/{z}/{x}/{y}.png`;
}

function cambiarModo(modo) {
  if (estado.modo === modo) return;
  estado.modo = modo;
  $('modo-comparar').setAttribute('aria-pressed', String(modo === 'comparar'));
  $('modo-desacuerdos').setAttribute('aria-pressed', String(modo === 'desacuerdos'));
  actualizarCapas();
}

function actualizarCapas() {
  const m = estado.mapa;
  if (estado.cortina) { estado.cortina.remove(); estado.cortina = null; }
  for (const clave of ['capaIzq', 'capaDer', 'capaMnc', 'capaDesacuerdo']) {
    if (estado[clave]) { m.removeLayer(estado[clave]); estado[clave] = null; }
  }
  cerrarInspector();
  cerrarFicha();
  $('map').classList.toggle('modo-desacuerdos', estado.modo === 'desacuerdos');

  // Fresh attempt: reset the no-tiles state machine.
  estado.algunTileCargado = false;
  estado.avisoCerrado = false;
  $('tarjeta-tiles').hidden = true;
  $('banda-tiles').hidden = true;
  dibujarZona(false);

  // crossOrigin es necesario para que el inspector pueda leer el tile en canvas;
  // requiere CORS habilitado en el bucket (SPEC §9).
  const opciones = { maxNativeZoom: ZOOM_MAX, maxZoom: ZOOM_MAX, crossOrigin: 'anonymous', opacity: 0.85 };

  if (estado.modo === 'desacuerdos') {
    // Las tres capas del inspector siguen cargadas, pero invisibles: el modo
    // Desacuerdos no es la cortina, es una lectura distinta de los mismos datos.
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
  } else {
    estado.capaIzq = L.tileLayer(urlTiles(`clasicas-${estado.clasificador}`), opciones).addTo(m);
    estado.capaDer = L.tileLayer(urlTiles(`embeddings-${estado.clasificador}`), opciones).addTo(m);
    // Capa invisible del MNC: no se ve, pero el inspector la lee para la fila "MNC (INTA)".
    estado.capaMnc = L.tileLayer(urlTiles('mnc'), { ...opciones, opacity: 0 }).addTo(m);
    estado.cortina = L.control.sideBySide(estado.capaIzq, estado.capaDer).addTo(m);
    // side-by-side fires dividermove during init and on every map move; only a
    // change in x means the user actually dragged the curtain.
    estado.cortinaX = null;
    estado.cortina.on('dividermove', (e) => {
      if (estado.cortinaX == null) { estado.cortinaX = e.x; return; }
      if (e.x !== estado.cortinaX) {
        estado.cortinaX = e.x;
        if (!$('onboarding').hidden && pasoActualOnboarding === 0) pasoOnboarding(1);
      }
    });

    // Si los tiles de los modelos no cargan, se explica en vez de fallar mudo.
    for (const capa of [estado.capaIzq, estado.capaDer]) {
      capa.on('tileload', tilesCargaron);
      capa.on('tileerror', fallaTiles);
    }

    $('linea-desacuerdo').hidden = true;
    $('casos').hidden = true;
    $('ficha-caso').hidden = true;
  }
}

// Department outline: always visible as a thin border (shows how far the
// classified area reaches); dashed + soft fill while tiles are missing.
function dibujarZona(destacada) {
  if (estado.capaZona) estado.capaZona.remove();
  const estilo = destacada
    ? { color: '#2f6c46', weight: 2, dashArray: '6 6', fillColor: '#2f6c46', fillOpacity: 0.08 }
    : { color: '#2f6c46', weight: 2, opacity: 0.7, fill: false };
  estado.capaZona = L.geoJSON(estado.zonas, {
    filter: (f) => f.properties.zona === estado.zona,
    style: estilo,
    interactive: false,
  }).addTo(estado.mapa);
}

// Honest copy per cause: pipeline never ran (dev) vs tiles unreachable (prod).
// The card explains; the band (stacked under other banners) stays one line.
function textoFallaTiles(compacto) {
  if (estado.metrics.generado == null) {
    return compacto
      ? 'Tiles sin generar — el mapa aparece cuando corra el pipeline.'
      : 'El pipeline todavía no corrió: los mapas aparecen cuando se generen los tiles.';
  }
  return compacto
    ? 'El mapa clasificado no cargó.'
    : `La zona marcada es ${NOMBRES[estado.zona]}. Revisá la conexión y reintentá.`;
}

function fallaTiles() {
  if (estado.algunTileCargado) return; // partial failure: keep the map, no card
  dibujarZona(true);
  // Retrying can't help while the pipeline hasn't produced tiles yet.
  const sinPipeline = estado.metrics.generado == null;
  $('tarjeta-tiles-reintentar').hidden = sinPipeline;
  $('banda-tiles-reintentar').hidden = sinPipeline;
  if (estado.avisoCerrado) {
    $('banda-tiles-texto').textContent = textoFallaTiles(true);
    $('banda-tiles').hidden = false;
  } else {
    $('tarjeta-tiles-texto').textContent = textoFallaTiles(false);
    $('tarjeta-tiles').hidden = false;
  }
}

function tilesCargaron() {
  estado.algunTileCargado = true;
  dibujarZona(false);
  $('tarjeta-tiles').hidden = true;
  $('banda-tiles').hidden = true;
}

function reintentarTiles() {
  actualizarCapas();
}

// ---------- 4. Inspector de píxel ----------

function claseDeColor(rgba) {
  if (!rgba || rgba[3] === 0) return null; // píxel transparente: fuera de zona
  for (const c of estado.leyenda.clases) {
    const hex = c.color.replace('#', '');
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    // Tolerancia chica: los tiles son PNG paletizado, el color llega exacto,
    // pero un reescalado del browser puede mover un LSB.
    if (Math.abs(r - rgba[0]) <= 2 && Math.abs(g - rgba[1]) <= 2 && Math.abs(b - rgba[2]) <= 2) {
      return c;
    }
  }
  return null;
}

function leerPixel(capa, latlng) {
  if (!capa) return null;
  const zoom = estado.mapa.getZoom();
  const tam = capa.getTileSize().x;
  const punto = estado.mapa.project(latlng, zoom);
  const clave = `${Math.floor(punto.x / tam)}:${Math.floor(punto.y / tam)}:${zoom}`;
  const tile = capa._tiles[clave];
  if (!tile || !tile.loaded) return null;
  try {
    const canvas = document.createElement('canvas');
    canvas.width = tam;
    canvas.height = tam;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(tile.el, 0, 0);
    const px = ctx.getImageData(Math.floor(punto.x % tam), Math.floor(punto.y % tam), 1, 1).data;
    return claseDeColor(px);
  } catch {
    return null; // tile sin CORS: no se puede leer, se muestra "—"
  }
}

function chipClase(clase) {
  if (!clase) return '—';
  const i = estado.leyenda.clases.findIndex((c) => c.codigo === clase.codigo);
  return `<span class="chip"><span class="muestra-color patron-${i}" style="--c:${clase.color}"></span>${clase.clase}</span>`;
}

function inspeccionarPixel(evento) {
  const { lat, lng } = evento.latlng;
  const izq = leerPixel(estado.capaIzq, evento.latlng);
  const der = leerPixel(estado.capaDer, evento.latlng);
  const mnc = leerPixel(estado.capaMnc, evento.latlng);

  // Three dashes tell the user nothing: outside the zone (or with no tiles)
  // show one honest sentence instead of an empty table.
  const vacio = !izq && !der && !mnc;
  $('insp-vacio').hidden = !vacio;
  $('insp-datos').hidden = vacio;

  $('insp-clasicas').innerHTML = chipClase(izq);
  $('insp-embeddings').innerHTML = chipClase(der);
  $('insp-mnc').innerHTML = chipClase(mnc);
  $('insp-desacuerdo').hidden = !(izq && der && izq.codigo !== der.codigo);
  $('insp-coords').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  $('inspector').hidden = false;

  if (estado.marcador) estado.marcador.remove();
  estado.marcador = L.marker(evento.latlng, {
    icon: L.divIcon({ className: 'marcador-pixel', iconSize: [14, 14] }),
    interactive: false,
  }).addTo(estado.mapa);
}

function cerrarInspector() {
  $('inspector').hidden = true;
  if (estado.marcador) { estado.marcador.remove(); estado.marcador = null; }
}

// ---------- 5. Leyenda y métricas ----------

function dibujarLeyenda() {
  $('leyenda-items').innerHTML = estado.leyenda.clases
    .map((c, i) =>
      `<li><span class="muestra-color patron-${i}" style="--c:${c.color}"></span>${c.clase}</li>`)
    .join('');
}

// null → "—". Un null nunca se muestra como cero (SPEC §7).
const fmtPct = (v) => (v == null ? '—' : `${(v * 100).toFixed(1)} %`);
const fmtNum = (v) => (v == null ? '—' : v.toFixed(3));

// Traducción en criollo del par clásicas-rf vs embeddings-rf: la comparación
// que más le importa a alguien que no lee una tabla de p-valores (SPEC §8).
function fraseCriolla(zona) {
  const comp = (zona.comparaciones || []).find((c) => c.a === 'clasicas-rf' && c.b === 'embeddings-rf');
  if (!comp) return '';
  const cl = zona.modelos['clasicas-rf'].acuerdo_mnc.overall;
  const em = zona.modelos['embeddings-rf'].acuerdo_mnc.overall;
  if (cl == null || em == null) return '';
  const p = comp.p;
  const pTxt = p < 0.001 ? '< 0,001' : `= ${p.toFixed(3).replace('.', ',')}`;
  const base = `De cada 100 píxeles, ${Math.round(cl * 100)} dicen lo mismo que el mapa del INTA con las
    features clásicas y ${Math.round(em * 100)} con AlphaEarth`;
  return comp.significativo
    ? `${base} — la diferencia es estadísticamente real (McNemar, p ${pTxt}).`
    : `${base} — y con esta muestra los dos enfoques no se distinguen (McNemar, p ${pTxt}).`;
}

function dibujarMetricas() {
  const zona = estado.metrics.zonas[estado.zona];
  const cont = $('metricas-contenido');
  if (!zona) { cont.innerHTML = '<p>—</p>'; return; }

  const modelos = [
    ['clasicas-rf', 'Clásicas · RF'],
    ['clasicas-knn', 'Clásicas · kNN'],
    ['embeddings-rf', 'AlphaEarth · RF'],
    ['embeddings-knn', 'AlphaEarth · kNN'],
  ];

  // Cuatro fichas, un vistazo: acuerdo con MNC por modelo, antes de la tabla completa.
  const fichas = modelos.map(([clave, nombre]) => {
    const a = zona.modelos[clave].acuerdo_mnc;
    const ic = a.ic95 && a.ic95[0] != null ? `IC 95: ${fmtPct(a.ic95[0])}–${fmtPct(a.ic95[1])}` : '';
    const familia = clave.startsWith('clasicas') ? 'clasicas' : 'embeddings';
    return `<div class="ficha-modelo ${familia}">
      <div class="ficha-label">${nombre}</div>
      <div class="ficha-num">${fmtPct(a.overall)}</div>
      <div class="ficha-ic">${ic}</div></div>`;
  }).join('');

  const frase = fraseCriolla(zona);

  // Cada número dice contra qué se midió: acuerdo con MNC ≠ accuracy (METODOLOGIA §1).
  const filas = modelos.map(([clave, nombre]) => {
    const m = zona.modelos[clave];
    const ic = m.accuracy_independiente.ic95;
    const icTxt = ic && ic[0] != null ? ` (${fmtPct(ic[0])}–${fmtPct(ic[1])})` : '';
    return `<tr><th scope="row">${nombre}</th>
      <td>${fmtPct(m.acuerdo_mnc.overall)}</td>
      <td>${fmtNum(m.acuerdo_mnc.kappa)}</td>
      <td>${fmtPct(m.accuracy_independiente.overall)}${icTxt}</td></tr>`;
  }).join('');

  const sinCorrer = estado.metrics.generado == null
    ? '<p class="nota-metrica"><strong>El benchmark todavía no corrió.</strong> Los números aparecen cuando el pipeline genere <code>data/metrics.json</code>.</p>'
    : `<p class="nota-metrica">Generado: ${estado.metrics.generado} · semilla ${estado.metrics.semilla}</p>`;

  cont.innerHTML = `
    ${sinCorrer}
    <div class="fichas-2x2">${fichas}</div>
    ${frase ? `<p class="nota-metrica frase-criolla">${frase}</p>` : ''}
    <table>
      <thead><tr><th>Modelo</th><th>Acuerdo con MNC</th><th>Kappa*</th><th>Accuracy independiente</th></tr></thead>
      <tbody>${filas}</tbody>
    </table>
    <p class="nota-metrica">El <em>acuerdo con el MNC</em> mide parecido con el mapa del INTA — que tiene
      su propio error — y no es accuracy. El <em>accuracy independiente</em> sale de puntos
      fotointerpretados a mano, con su intervalo de confianza del 95 %.</p>
    <p class="nota-metrica">*Kappa se reporta por convención; ninguna conclusión se apoya en él
      (Pontius &amp; Millones, 2011).</p>`;
}

// ---------- 6. Explicación ----------

const PASOS_ONBOARDING = [
  'Dos IA distintas clasificaron cada lote de esta zona. <b>Arrastrá la línea</b> y encontrá dónde no se ponen de acuerdo.',
  'Tocá cualquier lote para ver qué dijo cada una — y qué dice el mapa del INTA en ese mismo punto.',
];
const TOAST_CLF = {
  rf: 'RF: 300 reglas simples votan qué cultivo es — gana la mayoría',
  knn: 'kNN: busca los 5 lotes conocidos más parecidos y copia su etiqueta',
};

let pasoActualOnboarding = 0;
let toastTimeout = null;
let onboardingClickCierre = null; // click-on-map closer, armed only during the last step

function mostrarOnboarding() {
  if (localStorage.getItem('onboarding-visto')) return;
  pasoActualOnboarding = 0;
  pintarPasoOnboarding();
  $('onboarding').hidden = false;
}

function pintarPasoOnboarding() {
  $('onboarding-texto').innerHTML = PASOS_ONBOARDING[pasoActualOnboarding];
  $('onboarding-paso').textContent = `${pasoActualOnboarding + 1} de ${PASOS_ONBOARDING.length}`;
  $('onboarding-sig').textContent =
    pasoActualOnboarding === PASOS_ONBOARDING.length - 1 ? '¡Listo!' : 'Siguiente →';
}

function pasoOnboarding(n) {
  if ($('onboarding').hidden) return;
  if (n >= PASOS_ONBOARDING.length) { cerrarOnboarding(); return; }
  pasoActualOnboarding = n;
  pintarPasoOnboarding();
  // Only the last step closes on a map tap (a tap during step 0 is likely the
  // user reaching for the curtain, not asking to dismiss the onboarding).
  if (pasoActualOnboarding === PASOS_ONBOARDING.length - 1 && !onboardingClickCierre) {
    onboardingClickCierre = () => cerrarOnboarding();
    estado.mapa.once('click', onboardingClickCierre);
  }
}

function cerrarOnboarding() {
  $('onboarding').hidden = true;
  localStorage.setItem('onboarding-visto', '1');
  if (onboardingClickCierre) {
    estado.mapa.off('click', onboardingClickCierre);
    onboardingClickCierre = null;
  }
}

function mostrarToast(texto) {
  const toast = $('toast-clasificador');
  toast.textContent = texto;
  toast.classList.add('visible');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('visible'), 4000);
}

function cerrarAyuda() {
  $('panel-ayuda').hidden = true;
  $('btn-ayuda').setAttribute('aria-expanded', 'false');
}

// ---------- 7. Tour de casos ----------

// Cada caso: { zona, latlng: [lat, lng], zoom, titulo, texto }.
// TODO(task 8): casos reales aprobados por Mateo — hoy es un placeholder para
// probar el andamiaje (chips + ficha); dibujarCasos() los filtra por zona.
const CASOS = [];

let casosZona = []; // CASOS filtrados por la zona activa; mostrarCaso(i) indexa acá

function dibujarCasos() {
  casosZona = CASOS.filter((c) => c.zona === estado.zona);
  cerrarFicha();
  if (casosZona.length === 0) {
    $('casos').hidden = true;
    $('casos').innerHTML = '';
    return;
  }
  $('casos').innerHTML = casosZona
    .map((c, i) => `<button class="chip-caso" type="button" data-indice="${i}">${c.titulo}</button>`)
    .join('');
  $('casos').querySelectorAll('.chip-caso').forEach((btn) => {
    btn.addEventListener('click', () => mostrarCaso(Number(btn.dataset.indice)));
  });
  $('casos').hidden = false;
}

function mostrarCaso(i) {
  const caso = casosZona[i];
  if (!caso) return;
  estado.mapa.setView(caso.latlng, caso.zoom);
  $('ficha-caso-titulo').textContent = caso.titulo;
  $('ficha-caso-texto').textContent = caso.texto;
  $('ficha-caso').hidden = false;
}

function cerrarFicha() {
  $('ficha-caso').hidden = true;
}

document.addEventListener('DOMContentLoaded', arrancar);
