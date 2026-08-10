# Rediseño UI/UX del visor — spec de diseño

**Fecha:** 2026-08-09 · **Estado:** aprobado por Mateo (brainstorming con companion visual)
**Contexto:** el evento es el 12-13 de agosto; esto se implementa en una sesión, con riesgo acotado.

## Objetivo

Mejorar claridad, identidad y robustez del visor mobile-first sin tocar nada del benchmark:
mismo stack (HTML + JS plano + Leaflet), misma paleta de clases, mismos strings de método.
Decisiones tomadas sobre mockups: layout "C" (controles arriba, mapa libre), identidad
"Campo moderno", estado sin-tiles combinado (zona marcada → banda), cortina con asa visible.

## 1 · Layout (mobile primero, 390 px)

- **Header verde** (`#2f6c46`, texto blanco): título en una línea, bajada corta
  ("Dos modelos miran el mismo lote — compará vos"), y debajo una fila con los tres
  selectores como chips: Zona · Campaña · Clasificador. Los `<select>` nativos se conservan
  (accesibilidad y cero JS nuevo); solo cambia su presentación a chip redondeado.
- **Desaparece la barra inferior.** El mapa ocupa todo el alto restante.
- **Sobre el mapa:**
  - Etiquetas de cortina: píldora "Clásico S2" arriba a la izquierda, "AlphaEarth" arriba a
    la derecha (texto en verde y ocre respectivamente, fondo blanco, sombra suave). Hoy nada
    en el mapa dice qué lado es qué — es el hueco de claridad más grande.
  - **Leyenda colapsable**: chip flotante "▲ Clases" abajo a la izquierda; expande al panel
    actual (mismos patrones anti-daltonismo). Arranca expandida la primera visita y colapsada
    después (localStorage), para que el productor vea los colores sin taparle el mapa siempre.
  - **Botón Métricas flotante** abajo a la derecha (verde, píldora). Abre el bottom-sheet de
    métricas actual, sin cambios de contenido.
  - **Hint efímero**: "Arrastrá la cortina para comparar · tocá el mapa para inspeccionar"
    aparece al cargar y se desvanece tras la primera interacción con cortina o mapa (o a los
    10 s). Deja de ser un cartel permanente.
- **Inspector de píxel**: se ancla al borde inferior del mapa, ancho completo menos márgenes
  (hoy flota centrado a media pantalla). Mismo contenido: tres filas + desacuerdo + coords.
- **Desktop (≥700 px)**: mismo layout; el header limita el ancho de la fila de chips y la
  leyenda puede quedar expandida por defecto. Sin trabajo extra más allá del media query.

## 2 · Identidad "Campo moderno"

Tokens nuevos en `:root` de `styles.css` (los nombres existentes se conservan donde aplique):

- Fondo crudo `#f6f3ea`, panel blanco, tinta `#2b2b24`.
- Acento verde `#2f6c46` (ya existente, AA sobre blanco); acento secundario ocre `#8a5a1a`
  para "AlphaEarth" (AA sobre blanco).
- Radios generosos (chips y píldoras `999px`, tarjetas `12px`), sombras blandas.
- Tipografía: system-ui, pesos 600-800 para jerarquía. **Sin webfonts** (presupuesto de peso).
- La paleta de clases y los patrones de `leyenda.json` **no se tocan**.
- Contraste AA verificado en todo el chrome nuevo; foco visible: anillo blanco de 3 px sobre
  el header verde, anillo verde sobre fondos claros (regla actual).

## 3 · Cortina y selección

- **Divisor**: línea blanca de 3 px con sombra suave (override de `.leaflet-sbs-divider` en
  `styles.css`, no en vendor).
- **Asa**: círculo blanco de 44 px de área táctil con flechas ⇄ verdes, centrado sobre el
  divisor (estilizando el range input de `leaflet-side-by-side`; override en `styles.css`,
  `vendor/range.css` queda intacto). Hoy no hay asa visible y nada invita a arrastrar.
- **Marcador de píxel**: doble anillo blanco + tinta (reemplaza el círculo oscuro simple).
  No verde a propósito: se confundiría con la clase soja. Visible sobre las seis clases.
- **Chip/select activo**: fondo blanco + texto verde; hover/focus consistentes.

## 4 · Estado sin tiles (dev y producción)

Escenarios y tratamiento (decidido explícitamente en brainstorming):

1. **Falla total al cargar** (`tileerror` sin ningún tile cargado): se dibuja el polígono del
   departamento con borde punteado verde y rayado sutil, y una tarjeta anclada abajo explica
   y ofrece **Reintentar** (re-crea las capas) y **Cerrar**.
2. **Cerrada la tarjeta** (o falla parcial con tiles ya visibles): colapsa a una **banda
   persistente** bajo el header con el mismo reintento como link. No es un toast.
3. **Copy honesto por causa**, detectada con lo que ya expone la API:
   - `metrics.generado == null` → "El pipeline todavía no corrió. Los mapas aparecen cuando
     se generen los tiles." (estado de desarrollo)
   - si no → "El mapa clasificado no cargó. Revisá la conexión y reintentá." (producción)
4. **El borde de zona queda siempre** como capa fina permanente (también con tiles OK):
   muestra hasta dónde llega el área clasificada.

Soporte backend: nuevo endpoint **`GET /zonas`** en `api/main.py` que sirve
`data/zonas.geojson` (espejo de `/leyenda`; la verdad única sigue en `data/`). Test de
contrato en `tests/test_api.py` (200, FeatureCollection, dos features con `id` esperado).
La banda "Campaña 2025/26 sin validar" no cambia de comportamiento (SPEC §8), solo de estilo.

## 5 · Restricciones que se mantienen

- Sin dependencias nuevas, sin frameworks, sin build. Presupuesto: frontend + Leaflet
  < 300 KB transferidos.
- Strings visibles en español rioplatense; código y comentarios en inglés.
- Ninguna métrica contra el MNC se rotula "accuracy"; el contenido del panel de métricas no
  cambia.
- `prefers-reduced-motion` respetado en toda transición nueva (hint, tarjetas, asa).

## Archivos afectados

- `frontend/index.html` — reestructura header/controles, etiquetas de cortina, tarjeta y
  banda sin-tiles, chips flotantes.
- `frontend/styles.css` — tokens, header, chips, asa/divisor, inspector anclado, estados.
- `frontend/app.js` — hint efímero, leyenda colapsable, capa de zona (fetch `/zonas`),
  lógica de estados sin-tiles con reintento, marcador nuevo.
- `src/mapa_cultivos/api/main.py` + `tests/test_api.py` — endpoint `/zonas` y su test.
- `vendor/*` — **no se toca.**

## Criterios de aceptación

- En 390 px con Slow 4G: header + mapa + chips visibles sin scroll; cortina arrastrable con
  el pulgar desde el asa; etiquetas de lado legibles sobre ambos fondos.
- Sin tiles: nunca se ve "mapa vacío + silencio"; siempre hay zona marcada + explicación +
  reintento, con copy correcto según la causa.
- Con tiles: leyenda colapsable funciona, inspector anclado muestra las tres filas y el
  desacuerdo, marcador visible sobre cualquier clase.
- Contraste AA en chrome nuevo; foco visible en chips, asa, botones; patrones de clase
  intactos.
- `pytest` en verde incluyendo el contrato de `/zonas`.

## Fuera de alcance

Modo explorar, cambios al panel de métricas más allá del estilo, tiles vectoriales, PWA/
offline real, más zonas o campañas, cualquier cambio al pipeline o a los números.
