# CLAUDE.md — Contexto e instrucciones para Claude Code

## Qué es este proyecto

Clasificación supervisada de cultivos sobre dos departamentos de la pampa argentina (Río Cuarto,
Córdoba; Pergamino, Buenos Aires), corrida con dos juegos de features —Sentinel-2 clásico vs
Satellite Embeddings de AlphaEarth— y publicada como un visor web con cortina comparativa.

Es el **Nivel 3** de la escalera de proyectos de `../portfolio-agtech-escalera-proyectos.md`, y la
card correspondiente en el portfolio apunta a la demo de este repo.

**El proyecto no es el mapa: es el benchmark.** El mapa es cómo se muestra. Cualquier decisión que
mejore el visor a costa del rigor del benchmark está mal orientada.

**Deadline: el evento es el 12-13 de agosto de 2026 y el objetivo es 🟢 live.** La URL de este visor
tiene que estar viva el **viernes 7** para poder cargarla en `../portfolio/src/data/projects.ts`
antes de que la URL del portfolio se congele el sábado 8. Cronograma completo en
`docs/SPEC.md → Cronograma`.

Audiencia: las mismas tres personas que escanean el QR del portfolio. Un productor quiere ver su
zona pintada y entender los colores. Un CTO quiere ver que el pipeline es serio. Alguien de INTA
va a mirar directo la metodología — y es la persona más fácil de perder si algo está mal dicho.

## Prioridades (en este orden)

1. **Honestidad del método por encima del número.** Si un resultado es feo, se publica feo. Si una
   métrica no se puede llamar accuracy, no se la llama accuracy. Esta prioridad gana sobre todo lo
   demás, incluido el impacto de la demo.
2. **Que la demo no dependa de la red.** Los tiles son precomputados. Earth Engine solo se toca en
   el pipeline offline y en el modo explorar, que es degradable por diseño.
3. **Reproducibilidad.** Semilla fija, muestras versionadas, todo número regenerable con un comando.
   Un número que no se puede reproducir no se publica.

Recién después de estos tres viene la estética del visor.

## Convenciones de código

- Python 3.12 gestionado con `uv`. Dependencias en `pyproject.toml`, nunca `pip install` suelto.
- **Código y comentarios en inglés; todo string visible al usuario en español rioplatense** (voseo:
  "tocá el mapa", "dibujá tu lote"). Los nombres de módulos y de dominio van en español porque son
  términos del dominio (`zonas.py`, `muestras.py`, `leyenda.json`) — eso es deliberado, no una
  inconsistencia.
- **El cómputo pesado vive en Earth Engine.** Muestreo, entrenamiento e inferencia con
  `ee.Classifier`. Nunca bajar rasters completos ni reimplementar el clasificador en local.
  scikit-learn se usa **solo** para calcular métricas sobre la tabla de validación exportada.
- Un solo lugar para cada verdad: las geometrías en `data/zonas.geojson`, las clases y colores en
  `data/leyenda.json`, la configuración en `settings.py` vía variables de entorno.
- Frontend sin framework: HTML + JS plano + Leaflet. Mismo criterio de peso que `../monitoring`.
- Los cuatro modelos del 2×2 se definen en un solo lugar en `clasificar.py` y se iteran; no se
  copia y pega la corrida cuatro veces.

## Qué NO hacer

- **No comparar solo la diagonal del 2×2.** "RF con bandas vs kNN con embeddings" confunde el juego
  de features con el clasificador. Siempre las cuatro celdas, siempre comparando filas.
- **No llamarle "ground truth" al Mapa Nacional de Cultivos.** Es una capa de referencia con su
  propio error. Contra ella se mide *acuerdo*. La palabra accuracy queda reservada para el set
  independiente fotointerpretado. Esto aplica al código, a los docs y a los strings de la interfaz.
- **No cambiar la semilla de muestreo ni el split para mejorar un número.** Si el resultado cambia
  al cambiar la semilla, eso es el hallazgo y va reportado como varianza, no escondido.
- **No editar `data/metrics.json` ni las tablas de `docs/BENCHMARK.md` a mano.** Los regenera
  `scripts/02_benchmark.py`. Si hay que tocarlos a mano, el bug está en el script.
- No commitear la key del service account, GeoTIFFs, tiles ni assets exportados de GEE.
- No agregar frameworks de frontend, librerías de gráficos pesadas ni dependencias sin justificar
  peso contra beneficio.
- No ampliar el alcance a más departamentos, más campañas, detección de cambio o estimación de
  rinde. Eso son los Niveles 4 y 5, están en la escalera y tienen su propio repo.

## Definición de "hecho" para cualquier tarea

- El pipeline corre de punta a punta con los comandos de `make` documentados en el README
- Cualquier número nuevo salió de una corrida reproducible, no de una captura ni de una estimación
- `data/metrics.json` y `docs/BENCHMARK.md` quedaron regenerados desde esa corrida
- Ninguna métrica contra el MNC quedó rotulada como "accuracy"
- Verificado en viewport 390 px con throttling Slow 4G si se tocó el frontend
- Contraste AA y foco visible en cualquier elemento nuevo; la paleta de clases sigue siendo
  distinguible con daltonismo
- Los strings visibles nuevos están en español rioplatense
- Si se agregó una limitación conocida del método, quedó escrita en `docs/METODOLOGIA.md`

## Contexto de dominio útil

- **Campaña agrícola:** ciclo del 1 de julio al 30 de junio. No coincide con el año calendario, y
  ese desfase es un problema real con los embeddings de AlphaEarth, que son anuales por año
  calendario. Está documentado en `data/README.md` y discutido en `docs/METODOLOGIA.md`.
- **MNC (Mapa Nacional de Cultivos):** producto del INTA que mapea cultivos a nivel nacional por
  campaña, publicado en GeoINTA. Referencia principal de este proyecto. Trabajo de de Abelleyra,
  Banchero, Verón y equipo.
- **Lote:** parcela de campo. **Zona núcleo:** región agrícola principal (norte de Buenos Aires, sur
  de Santa Fe y Córdoba). **Doble cultivo:** trigo seguido de soja de segunda en la misma campaña.
- **Maní:** cultivo característico del sur de Córdoba, casi ausente del resto de la pampa. Es la
  clase minoritaria y la más difícil del problema — su firma se parece a la de la soja temprana.
- **Satellite Embeddings (AlphaEarth):** dataset `GOOGLE/SATELLITE_EMBEDDING`, 64 bandas a 10 m que
  codifican un año entero de observaciones multi-sensor en un vector por píxel. La promesa es que
  reemplazan el feature engineering manual. Verificar esa promesa sobre cultivos argentinos es
  exactamente el punto del proyecto.
- **NDVI:** índice de vegetación normalizado, `(B8 − B4) / (B8 + B4)`. Base de las features clásicas.

## Inputs que aporta Mateo (bloqueantes)

Mientras falten, van como `TODO:` explícito en el código o `PENDIENTE` en los docs, nunca como valor
plausible improvisado:

- Proyecto de Google Cloud con la API de Earth Engine habilitada y service account **registrado en
  Earth Engine** (registrar el service account es un paso aparte de crearlo)
- Capa del Mapa Nacional de Cultivos descargada de GeoINTA para la campaña 2024/25 — y confirmación
  de que esa campaña ya está publicada. Si no lo está, se cae a la última disponible: el año es un
  parámetro, no una constante
- Bucket de GCS para los tiles, con acceso público de lectura y CORS habilitado
- Los ~200 puntos de validación independiente fotointerpretados (ver `docs/METODOLOGIA.md`) — es
  trabajo manual y es el input que más tarda
- URL de producción del visor, confirmada antes del **viernes 7 de agosto**

## Flujo de trabajo sugerido

1. Ante una tarea de pipeline, leer primero `docs/SPEC.md` y `docs/METODOLOGIA.md` completos. Las
   decisiones de método ya están tomadas y argumentadas ahí; no se reabren sin motivo nuevo.
2. Proponer el plan en 2-3 líneas antes de escribir código si la tarea toca más de un módulo.
3. Los exports de Earth Engine tardan. Lanzarlos temprano y seguir con otra cosa mientras corren.
4. Después de implementar, correr el pipeline y reportar qué se verificó y con qué números — no
   "funciona", sino qué salió.
