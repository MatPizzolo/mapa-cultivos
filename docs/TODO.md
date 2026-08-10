# TODO — qué sigue y en qué orden

Estado al **martes 4 de agosto de 2026**. El cronograma completo y el orden de recorte están en
[`SPEC.md §10`](SPEC.md#10-cronograma); esto es la bajada operativa. La restricción dura es el
**viernes 7**: la URL del visor tiene que existir antes de que se congele el portfolio.

---

## Hecho ✅

- [x] Scaffolding del repo: `pyproject.toml` (uv, Python 3.12), `Makefile`, `.env.example`,
      `Dockerfile`, `.gitignore`
- [x] `settings.py`, `ee_client.py`, `zonas.py` (ventana de campaña + años de embedding, con tests)
- [x] `data/leyenda.json` completa y `data/metrics.json` en estado vacío (contrato SPEC §7)
- [x] API FastAPI: `/health`, `/metrics`, `/leyenda`, `/clasificar` (503 hasta la capa 4)
- [x] Frontend piso: cortina, inspector de píxel, panel de métricas, leyenda con patrones,
      banda de campaña sin validar — 54,8 KB gzip, 14 tests pasando

## Bloqueantes de Mateo 🔴

Sin esto el pipeline no corre. Mientras falten, el código falla explícito con `PENDIENTE`:

- [x] **Proyecto GCP** con la API de Earth Engine habilitada y service account **registrado en EE**
      (registrarlo es un paso aparte de crearlo) → completar `GEE_SERVICE_ACCOUNT` y `GEE_KEY_PATH`
      en `.env`
- [x] **Verificar HOY en GeoINTA** si el MNC 2024/25 está publicado. Si no, elegir la última campaña
      disponible y setear `MNC_CAMPANIA` — el año es un parámetro, no una constante
- [x] Descargar la capa del MNC para esa campaña
- [ ] Límites departamentales del IGN → `data/zonas.geojson` (features con property
      `"zona": "rio-cuarto" | "pergamino"`)
- [ ] **Bucket de GCS** para tiles, lectura pública y CORS habilitado para el dominio del visor
- [ ] Los ~200 puntos de validación independiente fotointerpretados (el input que más tarda —
      se puede empezar después del primer mapa clasificado)
- [ ] URL de producción confirmada antes del **viernes 7**

## Martes 4 — datos (el tramo más riesgoso)

- [ ] `referencia.py`: cargar la capa del MNC y remapearla a la leyenda de 6 clases
      (completar `mapeo_mnc` en `data/leyenda.json` con los códigos reales, no improvisados)
- [ ] `muestras.py`: muestreo estratificado (500/300 por clase por zona), erosión de bordes 20 m,
      bloques espaciales de 5×5 km, `SEED = 42`
- [ ] `scripts/01_muestrear.py` real → `data/muestras/{zona}_{campania}.csv` versionadas
- [ ] Chequear soporte de `maní`: si no llega a 100, se reporta como clase de bajo soporte
      (no se infla, no se sintetiza — METODOLOGIA §2.1)

## Miércoles 5 — features y primer modelo

- [ ] `features.clasicas()`: 6 ventanas fenológicas × (10 bandas + 4 índices) + 5 estadísticos
      de NDVI = 89 features, con Cloud Score+ ≥ 0.60
- [ ] `features.embeddings()`: concatenar los 2 años calendario que solapan la campaña = 128 features
- [ ] `clasificar.py`: las 4 celdas definidas en un solo lugar; z-score **solo** para clásicas+kNN,
      con media/desvío del set de entrenamiento (SPEC §5)
- [ ] Primer RF corriendo de punta a punta sobre Río Cuarto

## Jueves 6 — benchmark completo

- [ ] `evaluar.py`: matriz de confusión, overall + IC 95 %, F1/producer/user por clase con soporte,
      kappa (con su nota), McNemar entre celdas, split aleatorio como control
- [ ] `scripts/02_benchmark.py`: corre el 2×2 + la ablación de un año y **regenera**
      `data/metrics.json` y las tablas de `BENCHMARK.md` — nunca a mano
- [ ] `exportar.py` + `scripts/03_exportar_mapa.py`: lanzar los exports de GEE **a la noche**
      (su tiempo no se controla)

## Viernes 7 — tiles, visor y URL viva

- [ ] `scripts/04_tiles.py`: GeoTIFF → tiles XYZ zooms 9–13, PNG paletizado, subir al bucket con
      `Cache-Control: immutable` y el nombre de corrida en la ruta
- [ ] Configurar `TILES_BASE` y `CORRIDA` en `frontend/app.js`
- [ ] Tileset del MNC como pseudo-modelo para que el inspector muestre la fila "MNC (INTA)"
- [ ] Pasar la paleta por simulador de daltonismo (par riesgoso: soja/maní — SPEC §2);
      si no pasa, ajustar luminancia antes que matiz
- [ ] Deploy a Cloud Run y **URL viva hoy** → cargarla en `../portfolio/src/data/projects.ts`

## Sábado 8 — verificación

- [ ] `min-instances = 1` hasta el 14/8
- [ ] Verificar en celular real: viewport 390 px, throttling Slow 4G, LCP < 2.5 s
- [ ] Carga inicial < 300 KB sin tiles (hoy: 54,8 KB ✓) y < ~1 MB con tiles al zoom de entrada

## Lunes 10 – martes 11 — capas 2 a 4, en orden, con lo que sobre

- [ ] Capa 2: Pergamino con el mismo pipeline
- [ ] Capa 3: campaña 2025/26 como inferencia sin validar (la banda ya está en el visor)
- [ ] Capa 4: modo explorar — implementar `/clasificar` real (límite 5.000 ha, timeout 25 s,
      dentro de Argentina) y el dibujo de polígono en el frontend. **Primera en caer**
- [ ] Validación independiente: etiquetar los 200 puntos por zona; con < 100, se reporta solo
      acuerdo con MNC diciéndolo explícito (riesgos, SPEC §11)

## Deuda conocida (no bloquea, no se pierde)

- [ ] `docs/METODOLOGIA.md`: verificar cada cita contra la fuente antes de publicar; completar los
      dos `PENDIENTE` de referencias (accuracy del MNC y paper de AlphaEarth)
- [ ] Contraste AA y foco visible: revisar sobre el visor terminado, no solo sobre el esqueleto
- [ ] `frontend/vendor/`: son librerías de terceros (Leaflet 1.9.4 + side-by-side 2.2.0 adaptado a
      browser globals). No se editan a mano; si hay que actualizar, se vuelve a bajar del registry
