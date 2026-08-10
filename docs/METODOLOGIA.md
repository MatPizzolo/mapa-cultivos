# METODOLOGÍA

Este documento explica **por qué** el benchmark está armado así, y qué se puede y qué no se puede
concluir de sus números. Es el documento que se lee antes de discutir un resultado.

El proyecto parte del Módulo 3 de un curso de Google Earth Engine, que hace clasificación
supervisada con split aleatorio y valida contra sí mismo. Cada apartado de acá abajo es una
desviación deliberada de ese punto de partida. Las desviaciones son el trabajo.

> **Sobre las citas.** Las referencias del final son de trabajos reales, pero **hay que verificar
> cada cita contra la fuente antes de publicar nada** — sobre todo los números que se le atribuyan
> al Mapa Nacional de Cultivos. Este documento no reproduce ningún valor de terceros de memoria.

---

## 1. El Mapa Nacional de Cultivos es referencia, no verdad de campo

El Mapa Nacional de Cultivos (MNC) del INTA es la mejor capa disponible de cobertura agrícola
argentina por campaña. También es, él mismo, **el producto de un clasificador**: tiene un error
propio, no uniforme entre clases ni entre regiones, y su equipo lo reporta campaña por campaña.

Comparar la salida de un clasificador contra la salida de otro clasificador **no mide accuracy**.
Mide **acuerdo**. Son cosas distintas y confundirlas invalida la conclusión: supongamos que este mapa
coincidiera con el MNC en una proporción `X` de los píxeles. Eso no significa que acierte `X` de las
veces — significa que **se parece** al MNC en `X`, incluyendo parecerse en sus errores.

Entonces el proyecto reporta **dos métricas separadas, con nombres distintos, en columnas
distintas**:

| Métrica | Contra qué | Cómo se llama | Qué mide de verdad |
|---|---|---|---|
| **Acuerdo con el MNC** | Muestra estratificada sobre la capa del INTA | *acuerdo*, nunca *accuracy* | Cuánto se parece este mapa al producto nacional de referencia |
| **Accuracy independiente** | Puntos fotointerpretados a mano sobre imagen de alta resolución | *accuracy* | Cuánto acierta, con la mejor aproximación a verdad de campo que hay sin salir al lote |

El accuracy independiente es el número chico, caro y lento. Es también el único que se puede llamar
accuracy. Si el tiempo alcanza para uno solo, se hace ese y se dice explícitamente que falta el otro.

**Accuracy reportado por el equipo del MNC para la campaña usada: `PENDIENTE`** — leer de la
documentación del producto en GeoINTA y citarlo textual. Ese número es el techo implícito del
acuerdo: no tiene sentido celebrar un acuerdo del 95 % contra una capa cuyo propio accuracy es menor.

## 2. Muestreo

### 2.1 Estratificación

Muestreo estratificado por clase sobre la capa del MNC remapeada a la leyenda de seis clases
(ver [`SPEC.md → Leyenda`](SPEC.md#2-leyenda-de-clases)).

| Set | Tamaño objetivo | Mínimo aceptable por clase |
|---|---|---|
| Entrenamiento | 500 puntos por clase por zona | 100 |
| Validación contra MNC | 300 puntos por clase por zona | 100 |
| Validación independiente | 200 puntos por zona en total | 25 |

Estratificar por clase y no proporcionalmente al área es deliberado: `maní` y `pastura/verdeo` son
minoritarias, y una muestra proporcional dejaría sus métricas sin poder estadístico. La contrapartida
es que la muestra **no es representativa del área** y por lo tanto no se puede usar para estimar
superficie sembrada sin corregir por los pesos de estrato — que es exactamente lo que hace el
apartado 5.

**Si `maní` no llega al mínimo de 100:** se reporta como clase de bajo soporte con su intervalo de
confianza ensanchado. No se sobremuestrea de otra campaña, no se sintetizan puntos, no se la fusiona
con soja para que el número quede lindo.

### 2.2 Erosión de bordes

Los píxeles del borde de un lote son mezcla: parte cultivo, parte camino, alambrado o el lote
vecino. Entrenar con ellos mete ruido; validar con ellos castiga al modelo por algo que el dato no
resuelve a 10 m.

Antes de muestrear se aplica una **erosión de 2 píxeles (20 m)** sobre las regiones homogéneas de la
capa de referencia. Solo se muestrea en el interior. Consecuencia honesta que hay que declarar: **el
accuracy reportado es el accuracy en el interior de los lotes, no en los bordes**, y por lo tanto es
optimista respecto del desempeño sobre el mapa completo. Se dice en `BENCHMARK.md`, no se esconde.

### 2.3 Semilla

`SEED = 42`, fijo, en `settings.py`. Las tablas de muestras quedan **versionadas en el repo**
(`data/muestras/`), así que cualquiera puede reproducir los números exactos sin volver a muestrear.

Si un resultado cambia de manera relevante al cambiar la semilla, **ese es el hallazgo** y va
reportado como varianza entre corridas. No se busca la semilla que mejora el número.

## 3. Split espacial por bloques, no aleatorio

Un split aleatorio de píxeles infla el accuracy. La razón es la autocorrelación espacial: dos
píxeles vecinos del mismo lote son casi el mismo dato, y si uno cae en entrenamiento y el otro en
validación, el modelo está siendo evaluado sobre algo que ya vio. El número sube y no significa nada.

Este proyecto usa **bloques espaciales**: una grilla de **5 × 5 km** sobre la zona, y cada bloque
entero se asigna a entrenamiento o a validación, nunca partido. Ningún píxel de validación comparte
lote con uno de entrenamiento.

El accuracy medido así **va a ser más bajo** que el del split aleatorio. Es el número correcto. Si
alguien compara este benchmark contra uno publicado con split aleatorio, la diferencia de método
explica buena parte de la brecha, y eso hay que decirlo antes de que lo pregunten.

Como control, `BENCHMARK.md` reporta **también** el accuracy con split aleatorio, para cuantificar
cuánto exactamente infla. Esa diferencia es un resultado interesante por sí mismo.

## 4. Validación independiente

Los puntos que sí funcionan como verdad de campo aproximada:

- **200 puntos por zona**, muestreados al azar dentro de los estratos del mapa producido (no del
  MNC — muestrear sobre el mapa a evaluar es lo que permite la estimación de área del apartado 5).
- Etiquetados **a mano por fotointerpretación** sobre imagen de alta resolución, mirando además la
  curva de NDVI del píxel a lo largo de la campaña: la forma de la curva es lo que distingue maíz
  temprano de soja de primera cuando la imagen sola no alcanza.
- Los etiqueta Mateo. **Un único intérprete es una limitación real** —no hay acuerdo inter-observador
  que reportar— y va declarada como tal.
- Los puntos que el intérprete no puede resolver con confianza se marcan `indeterminado` y **se
  excluyen del cálculo**, reportando cuántos fueron. Forzar una etiqueta dudosa contamina la única
  métrica limpia que tiene el proyecto.

## 5. Métricas

### 5.1 Qué se reporta

- **Matriz de confusión** completa de cada uno de los cuatro modelos.
- **Overall accuracy** con **intervalo de confianza del 95 %**. Un accuracy sin intervalo, sobre
  muestras de este tamaño, no permite decir si dos modelos difieren.
- **F1, producer's accuracy y user's accuracy por clase**, con el soporte al lado. Un F1 sin soporte
  no se puede leer.
- **Kappa**, con la salvedad del apartado siguiente.

### 5.2 Sobre kappa

Kappa se reporta porque es lo que el curso enseña y lo que mucha gente del ambiente espera ver. Pero
está **seriamente cuestionado en la literatura de teledetección**: corrige por un "acuerdo por azar"
que no tiene interpretación clara en clasificación de coberturas, es fuertemente sensible a la
prevalencia de las clases, y en la práctica ordena los modelos casi igual que el overall accuracy —
con lo cual no agrega información y sí agrega confusión (Pontius & Millones, 2011).

**Ninguna conclusión de este proyecto se apoya en kappa.** Está en la tabla, con esta nota al lado.

### 5.3 Comparar dos modelos

Dos modelos evaluados sobre **la misma muestra** de validación no son independientes, así que
comparar sus intervalos de confianza por separado es incorrecto. Para decir si la diferencia entre
dos celdas del 2×2 es real se usa el **test de McNemar** sobre los aciertos y errores pareados.

Si la diferencia no es significativa, la conclusión que se publica es **"no se distinguen con esta
muestra"** — no el modelo que quedó medio punto arriba.

## 6. Estimación de superficie sembrada

Contar píxeles de cada clase y multiplicar por 100 m² **es un estimador sesgado**: los errores de
comisión y omisión no se cancelan, y una clase con mucha comisión aparece sistemáticamente más
grande de lo que es.

La superficie se estima con la **corrección por matriz de error de Olofsson et al. (2014)**, que usa
las proporciones estimadas a partir de la matriz de confusión y los pesos de estrato del mapa, y
produce además intervalos de confianza para el área de cada clase.

Esa área corregida se contrasta con dos referencias externas: el área del MNC en la misma zona y las
estimaciones agrícolas del MAGyP para el departamento. Que las tres coincidan razonablemente es la
mejor validación de sentido común que tiene el proyecto — y que **no** coincidan es un resultado
igual de publicable.

## 7. Limitaciones declaradas

Sin adornos. Van también en `BENCHMARK.md` y resumidas en el visor.

1. **Desfase calendario / campaña en los embeddings.** `GOOGLE/SATELLITE_EMBEDDING` es anual por año
   **calendario**; la campaña agrícola va de julio a junio. Ningún año calendario cubre una campaña.
   La configuración principal concatena los dos años que la solapan, lo que mete información de dos
   campañas parciales en el vector. Las features clásicas no tienen este problema: se recortan a la
   ventana exacta. **Es una desventaja estructural de los embeddings en agricultura de secano del
   hemisferio sur**, y la ablación con un solo año la cuantifica. Si los embeddings pierden, esta es
   la primera hipótesis a considerar antes de concluir que el modelo fundacional no sirve.
2. **Una sola campaña validada.** El benchmark corre sobre 2024/25. Un modelo que anda bien en una
   campaña puede no andar en otra: la 22/23 fue de sequía extrema y las firmas espectrales de ese
   año no se parecen a las de una campaña normal. Nada acá dice cómo se comporta bajo estrés hídrico.
3. **Dos departamentos no son la pampa.** Río Cuarto y Pergamino se eligieron por contraste, no por
   representatividad. No se extrapola a nivel nacional.
4. **El MNC arrastra su propio error** y el acuerdo hereda ese techo (apartado 1).
5. **Accuracy de interior de lote.** Por la erosión de bordes, el número no describe el desempeño
   sobre bordes ni sobre lotes chicos, donde el borde es proporcionalmente mucho más grande.
6. **Clasificación por píxel, sin contexto espacial.** No hay segmentación de lotes ni post-proceso
   de suavizado. El mapa va a tener sal y pimienta y eso es esperado — filtrarlo mejoraría la foto y
   cambiaría las métricas, así que no se filtra.
7. **Un solo fotointérprete** en la validación independiente (apartado 4).
8. **Los hiperparámetros no están tuneados.** Se usan valores razonables y fijos para los cuatro
   modelos. Un RF tuneado podría cambiar el orden. Lo que se compara son **juegos de features en
   igualdad de condiciones**, no el mejor modelo alcanzable con cada uno.
9. **`pastura/verdeo` no tiene soporte en el MNC 2024/25 de estas zonas.** El MNC publica invierno
   y verano por separado, y en los recortes de Río Cuarto y Pergamino no aparecen los códigos de
   verdeo (27/28) ni existe una clase de pastura perenne. La clase queda en la leyenda con soporte
   cero, fuera de los promedios macro: los modelos de esta corrida **no pueden predecirla**. Se
   revisa cuando exista la validación independiente, que sí puede fotointerpretar pasturas.
10. **La referencia se muestrea a la resolución del MNC (~25–30 m), no a 10 m.** Los mapas del MNC
    2024/25 (Zenodo `10.5281/zenodo.17652712`) se leen localmente, se cruzan invierno × verano para
    derivar la leyenda propia (reglas en `data/leyenda.json`) y se erosiona 1 píxel de esa grilla
    (~25–30 m) en lugar de los «2 px / 20 m» que la spec original enunciaba asumiendo dato de 10 m.
    Las features sí se muestrean a 10 m en los centros de píxel del MNC. El cruce de resoluciones
    agrega ruido de borde que la erosión mitiga pero no elimina.

## 8. Qué se puede concluir, y qué no

**Se puede concluir:** si, sobre estas dos zonas, esta campaña y este protocolo, los embeddings de
AlphaEarth alcanzan o superan a un juego de features clásicas cuidadosamente construido — y a qué
costo de esfuerzo de ingeniería.

**No se puede concluir:** que los embeddings sean mejores o peores "en general", ni que estos
resultados valgan para otra región, otra campaña u otro conjunto de clases. Tampoco se puede
concluir nada sobre el desempeño en campañas atípicas.

El valor del proyecto no es el número. Es que el número esté medido de una manera que se pueda
discutir.

## 9. Referencias

Verificar cada cita antes de publicar.

- **Mapa Nacional de Cultivos** — INTA, Programa Nacional de Agricultura. Equipo de de Abelleyra,
  Banchero, Verón y colaboradores. Distribuido por GeoINTA. `PENDIENTE`: citar la publicación
  metodológica y la documentación de la campaña usada.
- **Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014).**
  *Good practices for estimating area and assessing accuracy of land change.* Remote Sensing of
  Environment, 148, 42–57. — Base del apartado 6.
- **Pontius, R. G., & Millones, M. (2011).** *Death to Kappa: birth of quantity disagreement and
  allocation disagreement for accuracy assessment.* International Journal of Remote Sensing, 32(15),
  4407–4429. — Base del apartado 5.2.
- **Roberts, D. R., et al. (2017).** *Cross-validation strategies for data with temporal, spatial,
  hierarchical, or phylogenetic structure.* Ecography, 40(8), 913–929. — Base del apartado 3.
- **AlphaEarth Foundations / Satellite Embeddings** — Google DeepMind, 2025. Dataset
  `GOOGLE/SATELLITE_EMBEDDING` en el catálogo de Earth Engine. `PENDIENTE`: citar el paper original
  y la ficha del dataset.
- **Estimaciones Agrícolas** — MAGyP, serie por departamento. Usadas como contraste de área en el
  apartado 6.
