# Diseño — Explicación en capas, modo Desacuerdos y fichas 2×2

**Fecha:** 2026-08-10 · **Decidido con Mateo** vía maquetas (`.superpowers/brainstorm/`).
Tres features para el visor antes del evento del 12-13/8. Restricciones: sin Earth Engine
(cuota restringida), carga < 300 KB gzip, sin frameworks, strings en rioplatense, no se toca
el pipeline del benchmark ni `metrics.json`.

## 1. Explicación en capas (opción D)

Tres momentos, tres piezas chicas:

- **Onboarding, 2 pasos, solo primera visita** (localStorage). Tarjetas flotantes sobre el
  mapa atenuado pero visible; botón "Saltar" siempre presente. Paso 1: *"Dos IA distintas
  clasificaron cada lote de esta zona. Arrastrá la línea y encontrá dónde no se ponen de
  acuerdo."* Paso 2: *"Tocá cualquier lote para ver qué dijo cada una — y qué dice el mapa
  del INTA."* Reemplaza al hint actual. Enseña a usar, no teoría.
- **Labels que se explican solos.** Selector de clasificador: "Comité de reglas (RF)" /
  "Por similitud (kNN)". Al cambiarlo, línea efímera (~4 s, `role="status"`): RF → *"300
  reglas simples votan qué cultivo es — gana la mayoría"*; kNN → *"busca los 5 lotes
  conocidos más parecidos y copia su etiqueta"*. Sin globitos ⓘ.
- **Hoja «?» con la teoría** (botón en la topbar, mismo patrón de hoja que métricas):
  cuatro bloques en criollo — qué estás viendo · los dos juegos de features ("seis fotos del
  ciclo elegidas por agrónomos" vs "el resumen automático del año de Google") · los dos
  clasificadores · el MNC y por qué decimos **acuerdo y no accuracy**. Cierra con la
  atribución CC-BY del MNC (obligación de licencia): "Referencia: Mapa Nacional de Cultivos
  2024/25, INTA (de Abelleyra et al.), CC-BY 4.0" + link al repo.

## 2. Modo «Desacuerdos» (B con ficha de C)

- **Datos:** `scripts/05_desacuerdo.py` compara pares de fila de los GeoTIFFs ya exportados
  (clásicas-rf vs embeddings-rf; ídem kNN) y genera tilesets binarios
  `{zona}/{campania}/desacuerdo-{clasificador}/` con el tiler existente: píxel pintado donde
  difieren, transparente donde coinciden o donde alguno es nodata. Reporta el % de área en
  desacuerdo por zona/clasificador a stdout (se usa en la ficha del modo, no entra a
  `metrics.json`). El color del desacuerdo se elige con `validate_palette.js` contra la
  paleta de clases y el fondo desaturado (candidato: magenta `#E91E8C`; si falla, se ajusta).
- **UI:** segmented control "Comparar | Desacuerdos" en la topbar. En Desacuerdos: la cortina
  se retira, el mapa base queda desaturado (filtro CSS sobre el pane de tiles base), la capa
  magenta encima, y una línea fija: *"En magenta, los píxeles donde los dos enfoques no
  coinciden (X % del área)"*. El inspector sigue activo (capas de modelos invisibles debajo,
  como ya hace el MNC).
- **Tour:** 3 chips ("🥜 ¿Maní o soja?", "🌾 Doble cultivo", "🏘️ Borde") sobre el borde
  inferior del mapa. Cada uno vuela a un caso y abre una **ficha narrativa** (patrón de la
  opción C): título + 2 frases sobre qué modelo dice qué y por qué es interesante. Los casos
  se preseleccionan analizando parches grandes de desacuerdo en los rasters (numpy), se
  verifican visualmente, y **los textos se muestran a Mateo antes de fijarlos**. Si una
  categoría no aparece (p.ej. no hay caso urbano claro), se eligen 3 casos reales cualquiera
  sea su tema — no se inventa el relato.

## 3. Panel de métricas: fichas 2×2 (opción C)

- Cuatro tarjetas espejando la grilla del benchmark, arriba de la tabla actual: label
  ("Clásicas · RF"), número grande (acuerdo %), IC 95 chico. Border-left con el color de
  identidad. Debajo, la frase criolla: *"De cada 100 píxeles, 94 dicen lo mismo que el mapa
  del INTA con las features clásicas, 91 con AlphaEarth — y la diferencia es
  estadísticamente real (McNemar, p < 0,001)"* — generada de `metrics.json` (valores y p
  reales por zona; si p ≥ 0,05 la frase cambia a "no se distinguen con esta muestra").
  Los datos salen de `/metrics` como hasta ahora; `null` → "—".

## 4. Identidad de color teal/naranja (transversal)

El par actual verde `#2f6c46` / ocre `#8a5a1a` **falla CVD** (ΔE 5.0 protan, validador de
dataviz). Se reemplaza la identidad de modelos por **teal `#0d9488` (clásicas) / naranja
`#c2410c` (AlphaEarth)** — pasa los 6 chequeos en claro. Aplica a: etiquetas de la cortina,
fichas 2×2, y cualquier referencia futura a "lado clásico / lado AlphaEarth". La topbar verde
es marca, no dato: no cambia. La paleta de clases del mapa no cambia (vive en `leyenda.json`
y tiene su propio chequeo pendiente).

## Flujo de datos y errores

- Todo lo nuevo del frontend consume lo que ya existe (`/metrics`, `/leyenda`) + los
  tilesets nuevos del bucket. Cero requests nuevos al backend.
- Si los tiles de desacuerdo no cargan, el modo muestra el mismo patrón de aviso/reintento
  que ya tiene el modo Comparar. Si `metrics.json` tiene `null`, las fichas muestran "—" y
  la frase criolla no se renderiza.

## Testing y verificación

- `tests/test_desacuerdo.py`: con rasters sintéticos, el cruce marca exactamente los píxeles
  distintos y respeta nodata; % de desacuerdo correcto.
- Suite existente sigue verde; peso total < 300 KB gzip re-medido.
- Verificación manual en 390 px: onboarding, hoja «?», modo Desacuerdos, tour, fichas.
- Deploy: tiles nuevos al bucket (misma corrida `2026-08-09a`), nueva revisión de Cloud Run.

## Fuera de alcance

Modo explorar, campaña 25/26, superficie sembrada (espera Olofsson + validación
independiente), cambios a la paleta de clases del mapa.
