# PLAN.md — lol-prepartida

Plan de implementación. Antes de empezar lee `AGENTS.md`.
Toma la primera tarea sin marcar que no esté BLOQUEADA. Una tarea por sesión.

## 1. Estado

| Fase | Estado |
| --- | --- |
| 0. Fundamentos (ingesta, base local, datos estáticos) | Hecha |
| 1. Métricas del jugador y app provisional en Streamlit | Hecha |
| **1b. Página estática con diseño visual, publicada en GitHub Pages** | **En curso: tareas T01 a T13** |
| 2. Motor de reglas y base de conocimiento | BLOQUEADA: falta especificación del supervisor |
| 3. Briefing de champ select y hoja de compras | BLOQUEADA |
| 4. Estadísticas de LAN Bronce–Oro y baneos | BLOQUEADA |

## 2. Objetivo de la fase 1b

Reemplazar la app de Streamlit por una página estática en `docs/` que:

- muestre las métricas del jugador con imágenes del juego y gráficas;
- se publique en GitHub Pages y quede siempre disponible;
- se actualice con un solo comando local (`prepartida publicar`) y, más adelante,
  con un proceso programado en GitHub (T12).

**Arquitectura**

```
API de Riot -> ingest.py -> data/prepartida.duckdb -> exportar.py -> docs/data/*.json
                                                                          |
                                                     docs/index.html + js lee los JSON
```

La página no llama a la API de Riot ni guarda claves. Todas las imágenes vienen de
Data Dragon, el servidor oficial de recursos estáticos de Riot.

## 3. Contrato de datos (`docs/data/`)

Este contrato es fijo. Cambiarlo requiere aprobación del supervisor.

Reglas generales:
- UTF-8, `ensure_ascii=False`. Los valores faltantes van como `null`, nunca `NaN`.
- Números redondeados: minutos y promedios a 1 decimal; oro a entero.
- Fechas en ISO 8601 UTC: `"2026-11-15T23:10:00Z"`.
- Sin PUUID ni nombres de otros jugadores.

### 3.1 `meta.json`

```json
{
  "generado": "2026-11-16T20:00:00Z",
  "version_ddragon": "16.22.1",
  "jugador": {
    "game_name": "SithLordDropout", "tag_line": "LAN",
    "tier": "BRONZE", "division": "III", "lp": 22, "victorias": 31, "derrotas": 39
  },
  "perfil": {
    "pool": ["Ahri", "Cassiopeia", "Sylas", "Taliyah", "Tristana"],
    "rol_principal": "MIDDLE", "rol_secundario": "BOTTOM",
    "meta_cs_10": 70, "meta_muertes_14": 1, "partidas_por_sesion": 3, "desfase_horas": 10
  }
}
```

`jugador.tier` y los campos de rango son `null` si no hay rango de Solo/Dúo.

### 3.2 `partidas.json`

Arreglo ordenado por `inicio` ascendente. Un objeto por partida:

| Campo | Tipo | Origen |
| --- | --- | --- |
| `match_id` | texto | `partidas.match_id` |
| `inicio` | fecha | `partidas.inicio` |
| `dia_sesion` | `"AAAA-MM-DD"` | columna de `metricas.partidas_del_jugador` |
| `n_del_dia` | entero | ídem |
| `parche` | texto | ídem |
| `champion_id` | entero | `participantes.champion_id` del jugador |
| `campeon` | texto | `participantes.campeon` |
| `posicion` | `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `UTILITY` o `""` | ídem |
| `lado` | `"azul"` o `"rojo"` | ídem |
| `victoria` | booleano | ídem |
| `asesinatos`, `muertes`, `asistencias` | entero | ídem |
| `duracion_min`, `cs_min` | número | `metricas` |
| `rival_champion_id` | entero o `null` | rival de la misma posición y lado contrario |
| `rival` | texto o `null` | nombre del campeón rival |
| `cs_10`, `dif_oro_10`, `dif_oro_15` | número o `null` | `metricas` |
| `muertes_14` | entero | `metricas` |
| `primera_muerte_min` | número o `null` | `metricas` |
| `en_pool` | booleano | `metricas` |
| `items` | arreglo de enteros | `item0` a `item6`, sin ceros ni nulos |
| `hechizos` | arreglo de 2 enteros | `hechizo1`, `hechizo2` |
| `runa_clave`, `arbol_primario`, `arbol_secundario` | entero o `null` | `participantes` |

### 3.3 `curvas.json`

Objeto con `match_id` como llave. Índice del arreglo = minuto, desde 0, máximo 40 minutos.

```json
{ "LA1_123": { "oro": [500, 620], "cs": [0, 4], "dif_oro": [0, 35] } }
```

- `oro`: `cuadros.oro_total` del jugador.
- `cs`: `cuadros.cs + cuadros.cs_jungla` del jugador.
- `dif_oro`: oro del jugador menos oro del rival de posición en ese minuto; `null` en cada
  posición si la partida no tiene rival de posición.

### 3.4 `muertes.json`

Arreglo con todas las muertes del jugador (eventos `CHAMPION_KILL` cuyo `victimId` es su `participant_id`).

```json
[ { "match_id": "LA1_123", "minuto": 6.4, "x": 7200, "y": 7450 } ]
```

`x` e `y` salen de `detalle.position.x` y `detalle.position.y` del evento. Si faltan, se omite la muerte.

### 3.5 `compras.json`

Objeto con `match_id` como llave. Compras del jugador (eventos `ITEM_PURCHASED` con su `participantId`)
cuyo ítem tiene `items.oro_total >= 2200`. Las partidas sin ninguna compra de este tipo
no aparecen en el objeto: la página debe tratarlas como lista vacía. Es una aproximación de "ítem completo".

```json
{ "LA1_123": [ { "minuto": 11.2, "item_id": 3157 } ] }
```

### 3.6 `estaticos.json`

Solo los elementos referenciados por los otros archivos.

```json
{
  "campeones": { "103": { "clave": "Ahri", "nombre": "Ahri" } },
  "items":     { "3157": { "nombre": "Reloj de Arena de Zhonya" } },
  "runas":     { "8112": { "nombre": "Electrocutar", "icono": "perk-images/Styles/Domination/Electrocute/Electrocute.png" } },
  "arboles":   { "8100": { "nombre": "Dominación", "icono": "perk-images/Styles/7200_Domination.png" } },
  "hechizos":  { "4": { "clave": "SummonerFlash", "nombre": "Destello" } }
}
```

Origen:
- `campeones` e `items`: tablas `campeones` e `items` de la base.
- `runas`, `arboles`: `data/estaticos/<version>/runesReforged.json`. Cada elemento de la raíz es un
  árbol (`id`, `name`, `icon`); sus runas están en `slots[].runes[]` (`id`, `name`, `icon`).
- `hechizos`: `data/estaticos/<version>/summoner.json`, en `data.<clave>`; el número es el campo `key` (texto).

### 3.7 URLs de imágenes

`V` es `meta.version_ddragon`. Base: `https://ddragon.leagueoflegends.com`.

| Imagen | URL |
| --- | --- |
| Retrato de campeón | `/cdn/V/img/champion/<clave>.png` |
| Arte grande de campeón | `/cdn/img/champion/splash/<clave>_0.jpg` |
| Ítem | `/cdn/V/img/item/<item_id>.png` |
| Hechizo | `/cdn/V/img/spell/<clave>.png` |
| Runa o árbol | `/cdn/img/<icono>` |
| Minimapa | `/cdn/V/img/map/map11.png` |

Verifica cada patrón abriendo una URL real en el navegador la primera vez que lo uses.
Si alguno falla, detente y anótalo en la bitácora.

## 4. Diseño visual

Tema oscuro. Todos los valores viven en `docs/css/tokens.css` como variables CSS.

| Variable | Valor | Uso |
| --- | --- | --- |
| `--fondo` | `#0b1220` | fondo de página |
| `--panel` | `#131c2e` | tarjetas y paneles |
| `--borde` | `#24304a` | bordes y líneas de cuadrícula |
| `--texto` | `#e6ebf5` | texto principal |
| `--texto-suave` | `#93a0b8` | texto secundario |
| `--acento` | `#d4a94a` | títulos de sección, línea de meta |
| `--victoria` | `#4c9aff` | victoria, valores a favor |
| `--derrota` | `#ef6b73` | derrota, valores en contra |
| `--radio` | `10px` | esquinas |
| `--espacio` | `16px` | separación base |

- Tipografía: `system-ui, -apple-system, "Segoe UI", sans-serif`. Cuerpo 15 px, cifras grandes 28 px.
- Ancho máximo del contenido: 1200 px. Rejilla de tarjetas con `grid` y `auto-fill, minmax(260px, 1fr)`.
- Debe verse bien a 390 px de ancho (móvil): una columna, sin desplazamiento horizontal.
- Retratos de campeón: 48 px en listas, 72 px en tarjetas, esquinas redondeadas.
- Gráficas con Chart.js: fondo transparente, líneas de cuadrícula en `--borde`, texto en `--texto-suave`.
  Una idea por gráfica. Siempre con título y unidades en los ejes.

## 5. Tareas de la fase 1b

### [x] T01 — Repositorio Git

- Ejecuta `git init` en la raíz. Rama `main`.
- Agrega a `.gitignore`: `.DS_Store`, `node_modules/`. Confirma que ya están `.env`, `data/`, `.venv/`.
- Crea `BITACORA.md` con un título y nada más.
- Primer commit con todo lo versionable.

Hecho cuando:
- `git status` está limpio.
- `git ls-files | grep -E "^\.env$|^data/|^\.venv/"` no devuelve nada.

### [x] T02 — Exportador de datos

Crea `src/prepartida/exportar.py` y `tests/test_exportar.py`.

```python
def exportar(con: duckdb.DuckDBPyConnection, perfil: Perfil, static_dir: Path, destino: Path) -> dict[str, int]:
    """Escribe los seis JSON del contrato en `destino`. Devuelve el conteo de elementos por archivo."""
```

- Una función privada por archivo: `_meta`, `_partidas`, `_curvas`, `_muertes`, `_compras`, `_estaticos`.
- Reutiliza `metricas.partidas_del_jugador`. Para `champion_id`, `rival_champion_id`, ítems, hechizos
  y runas, agrega columnas a `metricas.SQL_PARTIDAS` (solo agregar; no cambies las existentes).
- `version_ddragon`: el valor más reciente de `campeones.version`.
- Convierte `NaN` y `NaT` a `null` antes de escribir.
- Si no hay jugador en la base, lanza `ValueError("No hay jugador en la base")`.

Pruebas (con la API simulada de `conftest.py` y una carpeta temporal):
- se crean los seis archivos y todos son JSON válido;
- `partidas.json` tiene 3 partidas con todos los campos de 3.2;
- ningún archivo contiene la cadena `puuid` ni `otro-` (PUUID simulados de otros jugadores);
- `curvas.json` de una partida tiene `dif_oro[15] == 750`;
- ningún archivo contiene `NaN`.

Para probar `estaticos`, crea en la carpeta temporal un `runesReforged.json` y un `summoner.json` mínimos.
Para probar `muertes`, puedes insertar un evento con `position` en la base de prueba.

Hecho cuando: `pytest` pasa completo.

### [x] T03 — Comandos `exportar` y `publicar`

En `cli.py`:
- `prepartida exportar`: abre la base en solo lectura, llama a `exportar(...)` con destino `docs/data`
  e imprime el conteo por archivo.
- `prepartida publicar`: ejecuta en orden ingesta, exportar, `git add docs/data`, y si hay cambios,
  `git commit -m "datos: <fecha>"` y `git push`. Si no hay remoto configurado, omite el push y lo dice.
  Si la ingesta falla por clave inválida, muestra el error y no continúa.

Hecho cuando:
- `prepartida exportar` genera los seis archivos con la base real.
- `pytest` pasa.

**PUNTO DE CONTROL 1.** Detente. El supervisor revisa los JSON reales antes de construir la página.

### [x] T03b — Correcciones del punto de control 1

Dos arreglos pedidos por el supervisor. Van en un solo commit.

1. **`estaticos.json` no incluye los ítems que solo aparecen en `compras.json`.**
   Con la base real falta el ítem `3003` (12 compras). En `exportar.py`, el conjunto de ítems
   de `_estaticos` debe unir los de `partidas[].items` con los `item_id` de todas las compras.
   Prueba nueva en `tests/test_exportar.py`: una compra de un ítem que no está en el inventario
   final de ninguna partida aparece en `estaticos.items`.
2. **`publicar` puede incluir en el commit archivos ajenos que ya estuvieran preparados.**
   En `_publicar_en_git`, limita el commit a la carpeta de datos:
   `git commit -m <mensaje> -- <destino>`. Prueba nueva en `tests/test_cli.py`: con otro archivo
   preparado (`git add`) antes de publicar, ese archivo no entra en el commit de datos.

Hecho cuando:
- `pytest` pasa.
- Tras `prepartida exportar` con la base real, todo `item_id` de `compras.json` y de
  `partidas[].items` existe en `estaticos.items`.

### [x] T04 — Esqueleto de la página

Crea:

```
docs/
  .nojekyll              (vacío)
  index.html
  css/tokens.css         variables de la sección 4
  css/base.css           estilos generales
  js/main.js             carga de datos y navegación
  js/datos.js            cargarDatos(): lee los seis JSON en paralelo
  js/imagenes.js         funciones de URL de la sección 3.7
  js/vistas/             una vista por archivo (vacías por ahora)
  vendor/chart.umd.js    Chart.js 4, copia local
```

- Descarga Chart.js 4 (archivo `chart.umd.js` de la distribución oficial) y guárdalo en `vendor/`.
  Anota la versión exacta en la bitácora. Esta dependencia está aprobada.
- Navegación por pestañas con el fragmento de la URL: `#inicio`, `#pool`, `#linea`, `#muertes`, `#partidas`.
- Cabecera fija: nombre del jugador, rango y fecha de la última actualización (`meta.generado`).
- Si falla la carga de datos, muestra un mensaje claro en la página.
- Todas las rutas son relativas (la página vivirá en una subcarpeta de GitHub Pages).

Hecho cuando:
- `python -m http.server 8000 -d docs` muestra la cabecera con datos reales y las cinco pestañas cambian de sección.
- No hay errores en la consola del navegador.

### [x] T05 — Funciones de cálculo

Crea `docs/js/calc.js` y `docs/js/calc.test.js`. Funciones puras, sin acceso al documento:

| Función | Devuelve |
| --- | --- |
| `tasaAjustada(victorias, partidas, prior = 10)` | `100 * (victorias + prior/2) / (partidas + prior)` |
| `agrupar(partidas, fnClave)` | por grupo: `partidas`, `victorias`, `tasa`, `tasaAjustada`, `cs10`, `difOro15`, `muertes14` (promedios ignorando `null`) |
| `resumen(partidas)` | totales y promedios generales, más `porDetras15` y `conDato15` |
| `tendencia(partidas, campo, ventana = 10)` | media móvil del campo por partida, ignorando `null` |
| `curvaPromedio(curvas, ids, campo, hastaMinuto = 20)` | promedio por minuto entre las partidas indicadas |
| `partidasDeHoy(partidas, perfil, ahora)` | partidas cuyo `dia_sesion` es el de `ahora` menos `desfase_horas` |
| `aCoordenadaMapa(x, y)` | `{ izquierda, arriba }` en porcentaje; ver nota |

Nota de `aCoordenadaMapa`: el mapa va aproximadamente de 0 a 14870 en `x` y de 0 a 14980 en `y`,
con origen abajo a la izquierda. `izquierda = x / 14870 * 100`, `arriba = (1 - y / 14980) * 100`.
Estos límites están **sin verificar**: se comprueban visualmente en T09.

Pruebas mínimas:
- `tasaAjustada(2, 3)` redondeado a 1 decimal es `53.8`; `tasaAjustada(0, 0)` es `50`.
- `agrupar` con 3 partidas (2 victorias) da `tasa` 66.7.
- los promedios ignoran `null`.
- `aCoordenadaMapa(0, 0)` da `{ izquierda: 0, arriba: 100 }`.

Hecho cuando: `node --test docs/js` pasa.

### [x] T06 — Vista Inicio

`docs/js/vistas/inicio.js`:
- **Aviso de sesión:** si las partidas de hoy son `>= perfil.partidas_por_sesion`, un aviso visible
  con cuántas lleva y cuántas ganó.
- **Cuatro indicadores:** CS al minuto 10 (contra `meta_cs_10`), oro al minuto 15 frente al rival
  (con "por detrás en N de M"), muertes antes del minuto 14 (contra `meta_muertes_14`),
  y tasa de victorias dentro del pool. Cada uno con su número de partidas y una minigráfica de
  `tendencia` de las últimas 30 partidas.
- **Gráfica de progreso:** media móvil de 10 partidas del CS al minuto 10, con la meta como línea
  horizontal en `--acento`.
- **Pool contra fuera del pool:** dos barras con tasa y número de partidas.

Hecho cuando:
- Con la base real: CS al 10 = 55.0, oro al 15 = −414, "por detrás en 47 de 74", muertes = 1.52.
  (Valores al 16 de noviembre de 2026; cambian al ingerir partidas nuevas.)
- Se ve bien a 390 px de ancho.

**PUNTO DE CONTROL 2.** Detente. El supervisor revisa el diseño visual antes de replicarlo en las demás vistas.

### [x] T06b — Correcciones del punto de control 2

La vista Inicio no cumple "se ve bien": el supervisor la renderizó y la página mide 11.142 px de
alto a 1280 px de ancho y 28.213 px a 390 px. Arreglos, en un solo commit:

1. **Gráficas sin altura fija.** Los `canvas` crecen sin límite (minigráficas de 7.500 px, gráficas
   de 2.300 px). Regla para toda la página, también en T07 a T10: cada `canvas` va dentro de un
   contenedor propio con `position: relative` y altura fija en CSS (minigráfica 44 px; gráfica
   normal 260 px; 220 px por debajo de 600 px de ancho). No asignes `canvas.height` a mano.
   Mantén `responsive: true` y `maintainAspectRatio: false`.
2. **Indicadores.**
   - La cifra principal va a 28 px y en negrita (sección 4).
   - Formato: CS al 10 con 1 decimal (`55.0`); oro como entero con signo (`−414`); muertes con
     2 decimales (`1.52`); tasa con signo de porcentaje (`48.2 %`).
   - Quita la línea repetida de partidas: cada tarjeta muestra el número de partidas una sola vez.
   - CS y muertes muestran la diferencia con la meta en texto: "15.0 por debajo de la meta de 70",
     "0.52 por encima de la meta de 1".
   - La tasa dentro del pool muestra "27 de 56 ganadas".
3. **Cabecera.** Rango legible: "Bronce III · 22 LP · 31 victorias, 39 derrotas". Traduce el tier
   (IRON Hierro, BRONZE Bronce, SILVER Plata, GOLD Oro, PLATINUM Platino, EMERALD Esmeralda,
   DIAMOND Diamante, MASTER Maestro, GRANDMASTER Gran Maestro, CHALLENGER Retador).
4. **Título de la sección:** "Resumen", no "Resumen de sesión".
5. **Gráfica de progreso:** título, eje Y con la unidad ("CS al minuto 10"), eje X con como mucho
   8 etiquetas, y la línea de meta rotulada "Meta 70".
6. **Pool contra fuera del pool:** dos barras horizontales delgadas (contenedor de 120 px de alto),
   cada una con su texto "48.2 % · 27 de 56" y "33.3 % · 7 de 21". Eje de 0 a 100 %, sin invertir.
7. **Franja del pool.** Bajo los indicadores, una fila con los retratos (48 px) de los campeones de
   `perfil.pool`, cada uno con su nombre y sus partidas, que enlaza a `#pool`. Usa `imagenes.js`.
   Si la imagen no carga, se muestra el nombre.
8. **Datos sin regenerar.** `docs/data/estaticos.json` sigue sin el ítem `3003`: tras T03b no se
   volvió a ejecutar `prepartida exportar` sobre `docs/data`. Ejecútalo y versiona el resultado.

Hecho cuando:
- En el navegador, a 1280 px de ancho, la vista Inicio completa mide menos de 1.800 px de alto;
  a 390 px, menos de 3.000 px. Compruébalo en la consola con
  `document.documentElement.scrollHeight` y anota los dos valores en la bitácora.
- Ningún `canvas` mide más de 300 px de alto:
  `Math.max(...[...document.querySelectorAll("canvas")].map(c => c.clientHeight))`.
- `"3003" in estaticos.items` es verdadero en `docs/data/estaticos.json`.
- `pytest` y `node --test docs/js/calc.test.js` pasan.

**PUNTO DE CONTROL 2 (repetido).** Detente. El supervisor vuelve a renderizar la página.

### [x] T06c — Correcciones del segundo repaso del punto de control 2

El supervisor midió la página en un navegador real (servidor local). Resultado de T06b: a 390 px mide
2.437 px (cumple, < 3.000) y a 1280 px mide 1.960 px (NO cumple, < 1.800). Ningún canvas pasa de
300 px, pero hay defectos. Causa común: `inicio.js` usa clases que no existen en ninguna hoja de
estilo (`indicadores`, `franja-pool`, `carta-pool-fila`, `carta-pool`, `retrato-pool`,
`etiqueta-franja`, `nombre-pool`, `partidas-pool`), así que los retratos salen a 128 px apilados.
Arreglos, en un solo commit (incluye el archivo `docs/js/vistas/pool.js`, ver nota abajo):

1. **CSS de las clases faltantes** en `docs/css/base.css`:
   - `.indicadores`: `display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
     gap: var(--espacio)`. A 1280 px las cuatro tarjetas van en una fila; a 390 px en una columna.
   - `.franja-pool`: fila horizontal con `flex-wrap`. `.carta-pool`: retrato de 48 px (`.retrato-pool`
     con `width: 48px; height: 48px; border-radius: var(--radio)`), nombre y partidas a su lado.
     `.carta-pool-fila` en fila con `gap` de 12 px.
2. **Cuarto canvas de 150 px.** La tarjeta "Tasa dentro del pool" pasa `[]` como serie y deja un canvas
   vacío con la altura por defecto. Si no hay serie, no crees el contenedor `.minigrafica` ni el
   canvas. Si se quiere minigráfica en esa tarjeta, pasa la tasa móvil de las últimas partidas del pool.
3. **Minigráficas ilegibles.** Se ven como líneas verticales finas. Revisa que `crearSparkline` reciba
   un valor por partida (últimas 20), con `tension` baja, `pointRadius: 0` y que el ancho del contenedor
   no sea 0 al crear la gráfica. Captura de pantalla de una tarjeta a 1280 px en la bitácora.
4. **Cabecera.** A ancho intermedio el rango choca con "Actualizado". Dale `gap: 16px` y
   `flex-wrap: wrap` al contenido, y que el rango pueda partirse en dos líneas.
5. **Cifras de la tasa del pool coherentes.** El indicador muestra 48.5 % y las barras 48.2 %: usa un
   solo valor y di cuál es. Regla: el indicador y las barras muestran la tasa cruda (victorias entre
   partidas) y la etiqueta lo dice.
6. **Texto de pool contra fuera del pool.** Hoy dice "56 de 77" y "21 de 77" (denominador total).
   Debe decir "27 de 56" y "7 de 21" (victorias de partidas del grupo), como pedía T06b punto 6.
7. **Altura a 1280 px.** Con el grid del punto 1 y los retratos de 48 px la página debe quedar por
   debajo de 1.800 px; si no, reduce la gráfica de progreso a 220 px.

Hecho cuando (mide en un navegador real y anota los valores en la bitácora; si no tienes
navegador, dilo y detente, no marques la tarea):
- A 1280 px: `document.documentElement.scrollHeight` < 1.800; las 4 tarjetas en una fila.
- A 390 px: < 3.000, sin desplazamiento horizontal.
- `[...document.querySelectorAll("canvas")].map(c => c.clientHeight)` no tiene valores de 150.
- Los retratos de la franja miden 48 px y están en una fila.
- `git status` no muestra `docs/js/vistas/pool.js` sin versionar.
- `pytest` y `node --test docs/js/calc.test.js` pasan.

Nota del supervisor: el commit de T06b borró `docs/js/vistas/pool.js` y `main.js` lo importa; la página
quedó rota ("No se pudieron cargar los datos"). El supervisor creó un `pool.js` vacío para poder
revisar. T07 lo llenará; no lo borres.

### [x] T06d — Colores de las gráficas y minigráficas

El supervisor midió T06c en un navegador real: 1280 px → 925 px de alto; 390 px → 1.763 px; canvas de
44, 44, 44, 44, 260 y 120 px; cuatro tarjetas en una fila; retratos de 48 px; `pool.js` versionado.
Eso cumple, y T06c queda marcada. Quedan dos defectos de las gráficas, con causa conocida:

1. **Chart.js no entiende `var(--token)`.** Todos los `color`, `borderColor` y `backgroundColor` de las
   gráficas son cadenas `"var(--...)"` (ver `inicio.js`). Dentro de un `canvas` eso no se resuelve: las
   barras de "Pool vs fuera del pool" salen negras, y los textos, ejes y rejillas salen en el gris por
   defecto de Chart.js, ilegibles sobre el fondo oscuro. Arreglo: crea `docs/js/tema.js` con
   `export function token(nombre) { return getComputedStyle(document.documentElement).getPropertyValue("--" + nombre).trim(); }`
   y úsalo en TODAS las opciones de Chart.js (`token("texto-suave")`, `token("borde")`, `token("victoria")`,
   `token("derrota")`, `token("acento")`, `token("texto")`). Además, al inicio de `main.js` pon
   `Chart.defaults.color = token("texto-suave")` y `Chart.defaults.borderColor = token("borde")`.
   Regla para T07 a T10: ninguna gráfica usa cadenas `var(...)`. Las tarjetas HTML sí pueden usarlas en CSS.
2. **Minigráficas como líneas verticales.** `crearSparkline` pasa datos `{x, y}` y deja la escala X como
   categórica, y todos los puntos caen en una sola columna. Declara `scales: { x: { type: "linear", display: false },
   y: { display: false } }`. Ajusta el eje Y al rango de los datos (`grace: "10%"`). Con `null` en la serie, usa
   `spanGaps: true`.
3. **Cabecera.** Falta el separador: debe leer "Bronce III · 22 LP · 31 victorias, 39 derrotas".

Hecho cuando (medido en un navegador real, con captura o descripción de lo que se ve):
- Las barras de "Pool vs fuera del pool" son azul y gris claro, no negras; los textos de ejes y leyenda se leen.
- Cada minigráfica muestra una línea que recorre el ancho de la tarjeta, no una línea vertical.
- `grep -n "var(--" docs/js/vistas/*.js` no devuelve opciones de Chart.js.
- Alturas de página y de canvas siguen igual que en T06c (925 px y 1.763 px, tolerancia 10 %).
- `pytest` y `node --test docs/js/calc.test.js` pasan.

**PUNTO DE CONTROL 2 (tercer repaso).** Detente. El supervisor revisa las gráficas; con su visto bueno
sigue T07.

> **Nota del supervisor para T07 (dos retoques menores de Inicio, mismo commit):** la cabecera lee
> "Bronce · III · 22 LP", y debe leer "Bronce III · 22 LP" (sin punto entre el tier y la división); y
> los textos bajo las barras de "Pool vs fuera del pool" salen pegados ("27 de 56 Fuera del pool"),
> sepáralos con un espacio de 24 px o en dos líneas.

### [x] T07 — Vista Pool

`docs/js/vistas/pool.js`:
- Una tarjeta por combinación campeón–posición del pool, ordenadas por partidas.
- Cada tarjeta: retrato, nombre, posición, partidas, victorias, tasa ajustada, CS al 10,
  oro al 15 y muertes antes del 14. Etiqueta "muestra pequeña" con menos de 10 partidas.
- Indicador de línea: barra horizontal centrada en cero con el oro al 15 (a favor en `--victoria`,
  en contra en `--derrota`), con el número escrito.
- Sección plegable "Fuera del pool" con las mismas tarjetas en tamaño reducido.

Hecho cuando: las cifras de Ahri MIDDLE coinciden con `prepartida estado`.

### [x] T07b — Correcciones de la vista Pool

El supervisor abrió `#pool` en un navegador real. Antes de revisar tuvo que borrar una línea de
`docs/js/main.js` (declaración doble de `const partes`, "Identifier 'partes' has already been
declared"), que dejaba TODA la página en "Cargando...". Ese arreglo ya está en el árbol de trabajo
(sin commit): inclúyelo en el commit de esta tarea. Ahora la vista carga, pero:

1. **Las cifras de las tarjetas salen vacías.** `pool.js` lee `tasa_ajustada`, `cs_10`, `dif_oro_15`,
   `muertes_14`, pero `agrupar()` de `calc.js` devuelve `tasaAjustada`, `cs10`, `difOro15`, `muertes14`
   (camelCase). Resultado: "—%", "—", y oro "0" en todas las tarjetas, y las barras del indicador de línea
   vacías. Usa los nombres que devuelve `agrupar()`. No cambies `calc.js` ni sus pruebas.
2. **Muertes con 2 decimales.** `promedio()` redondea a 1 decimal; en esa vista las muertes antes del 14
   deben verse con 2 decimales (p. ej. 1.52). Si hace falta, `agrupar()` devuelve sin redondear y las
   vistas redondean al mostrar; ajusta `calc.test.js` si cambia.
3. **Orden.** Las tarjetas deben ir de más a menos partidas (hoy: Ahri 31, Tristana 6, Cassiopeia 7...).
   Ordena en `pool.js` con `.sort((a, b) => b.partidas - a.partidas)`.
4. **Formato.** Tasa ajustada con un espacio antes del signo ("46.3 %"); oro con signo "−350" /
   "+120" (usa el signo menos "−"); "Fuera del pool (9 combinaciones)" (el plural era "combinacións").
5. **Indicador de línea.** La barra se ve como un punto. Con las cifras correctas debe verse una barra
   horizontal centrada en cero con el número al lado (a favor azul, en contra rojo).
6. **Verificación.** El comando `node --check archivo.js` NO detecta errores de módulos ES. Usa
   `node --input-type=module --check < docs/js/main.js` (y lo mismo con cada archivo de `docs/js`), y
   además abre la página y mira la consola. Si no tienes navegador, DILO y no marques la tarea.

Hecho cuando (medido en un navegador real; si no hay navegador, no marques):
- Ahri MIDDLE muestra 31 partidas, 14 victorias, tasa ajustada 46.3 %, oro al 15 de −350 (compara con
  `python3 -m prepartida estado` o el comando equivalente), y su barra de oro es visible.
- Ninguna tarjeta del pool muestra "—" salvo que el dato no exista.
- La página `#pool` a 390 px de ancho mide menos de 4.500 px y no desborda horizontalmente.
- `pytest` y `node --test docs/js/calc.test.js` pasan.

> **Retoque pendiente de la vista Pool (haz esto primero, en el commit de T08):** el indicador de línea
> de las tarjetas no se lee bien. (a) El número ("−350") queda pegado a la esquina inferior izquierda
> de la tarjeta, lejos de la barra: debe ir junto a la barra, en su extremo. (b) No se ve la línea del cero:
> dibuja una línea vertical fina (`--borde`) en el centro del contenedor, de 20 px de alto. (c) Las barras
> son muy cortas (Ahri −350 mide ~24 px): la escala común usa el máximo de todas las combinaciones
> (hasta ±1.609) y casi todo queda diminuto; usa el máximo de las combinaciones con 10 o más partidas, o
> un valor fijo de ±1.000 con la barra recortada a ese tope. (d) A 390 px agrupa las seis cifras de la
> tarjeta en 3 filas de 2 como ahora, pero reduce el espacio vertical (cada tarjeta mide ~360 px).
> Medición de referencia: `#pool` mide 2.849 px a 390 px con "Fuera del pool" plegado.

### [x] T08 — Vista Línea

`docs/js/vistas/linea.js`:
- Selector de campeón (pool) y de posición.
- **Diferencia de oro frente al rival, minuto 0 a 20:** línea promedio de las partidas seleccionadas,
  línea de cero marcada y área sombreada a favor o en contra.
- **CS acumulado, minuto 0 a 20:** línea promedio y línea de meta recta de 0 a `meta_cs_10` en el minuto 10,
  prolongada con la misma pendiente.
- **Según muertes tempranas:** tres barras (0, 1, 2 o más muertes antes del 14) con tasa, partidas
  y oro medio al 15.

Hecho cuando: cambiar el selector actualiza las tres gráficas y cada una indica cuántas partidas promedia.

### [x] T08b — Correcciones de la vista Línea y del indicador de Pool

El supervisor abrió `#linea` y `#pool` en un navegador real. Las tres gráficas de Línea se dibujan
bien al cargar (oro vs rival, CS con meta, barras por muertes tempranas), pero:

1. **Los selectores no funcionan.** Al cambiar campeón o posición la consola da
   `ReferenceError: filtrar is not defined` (`linea.js` líneas 350 y 355). Escribe la función
   `filtrar(partidas, campeon, posicion)` ("Todos"/"Todas" no filtran) y llama a
   `destruirGraficas()` antes de volver a dibujar. Si el filtro deja 0 partidas, muestra el texto
   "Sin partidas para esta selección" en lugar de las gráficas.
2. **Valor por defecto.** "Todos los campeones" debe significar "todo el pool" (`en_pool`), no las 77
   partidas: es la vista para entrenar el pool. Añade una opción aparte "Todas las partidas" al final.
3. **Barras por muertes tempranas.** El texto con partidas y oro medio solo está en el tooltip. Ponlo
   visible en la etiqueta de cada barra: "0 muertes · 25 partidas · +120 oro" (usa `−` para negativos).
   Barra azul si su tasa ≥ 50 %, roja si < 50 %.
4. **Indicador de línea de Pool (retoque de T08 mal resuelto).** Hoy la escala usa el máximo de las
   combinaciones con 10+ partidas, que es solo Ahri, así que Ahri (−350) llena media barra y una
   combinación de +57 ya mide 24 px. Usa una escala FIJA de ±1.000 (recorta en el tope). Además el
   número de Ahri ("−350") se sale por el borde izquierdo de la tarjeta: el número debe quedar siempre
   dentro de la tarjeta (`overflow: hidden` en el contenedor y número posicionado con `clamp`).

Hecho cuando (medido en un navegador real; si no hay, dilo y no marques):
- Cambiar a Ahri / MIDDLE no produce errores en la consola y las tres gráficas dicen
  "Promedio de 31 partidas".
- Con el valor por defecto dicen "Promedio de 56 partidas".
- La barra de Ahri en Pool mide aproximadamente el 17 % del ancho del contenedor (350/1000 × 50 %), y
  ningún número del indicador sale de su tarjeta.
- `pytest` y `node --test docs/js/calc.test.js` pasan.

> **Retoques pendientes (haz esto primero, en el commit de T09):** (a) en Línea, las etiquetas de las
> barras por muertes tempranas se cortan por la izquierda ("ertes · 8 partidas · +778 oro"): pon el
> texto en dos líneas (`["0 muertes", "8 partidas · +778 oro"]`) o reserva ancho para el eje Y
> (`afterFit` o `scales.y.ticks.padding`). (b) En Pool, el número de una barra que llega al tope
> (Tristana +1026) se sale de la tarjeta: cuando la barra pase del 40 % del contenedor, pon el número
> dentro de la barra (texto oscuro) o del lado contrario del cero.

### [x] T09 — Vista Muertes

`docs/js/vistas/muertes.js`:
- Minimapa cuadrado con las muertes como puntos, posicionadas con `aCoordenadaMapa`.
- Filtros: campeón, lado (azul o rojo), tramo de tiempo (0–14, 14–25, 25 en adelante). Por defecto 0–14.
- Al pasar sobre un punto: campeón, rival, minuto y resultado.
- Conteo visible de muertes mostradas y de partidas.

**Verificación obligatoria de coordenadas:** las muertes de un jugador de mid antes del minuto 10
deben caer en su mayoría sobre la diagonal central del mapa. Si aparecen desplazadas o reflejadas,
detente y anótalo: no ajustes los límites a ojo.

Hecho cuando: los filtros funcionan y la verificación de coordenadas se cumple.

> **Retoques pendientes de Muertes (haz esto primero, en el commit de T10; incluye el cambio del
> supervisor en `docs/css/base.css`, que ya está en el árbol sin commit):** (a) en el selector de
> campeón, "Todos" incluye campeones de fuera del pool (MissFortune, etc.): llama a esa opción
> "Todas las partidas" y añade "Todo el pool" como valor por defecto, igual que en Línea. (b) En el
> título de cada punto usa el nombre visible del campeón (`estaticos.campeones[clave].nombre`, p. ej.
> "Miss Fortune", no "MissFortune"); igual en las demás vistas que muestren nombres. (c) Leyenda bajo el
> mapa: punto azul = victoria, punto rojo = derrota.

### [x] T10 — Vista Partidas

`docs/js/vistas/partidas.js`:
- Lista de las últimas 30 partidas, de la más reciente a la más antigua: fecha local, resultado
  (texto y color), retrato propio, retrato del rival, posición, lado, KDA (asesinatos/muertes/asistencias),
  CS al 10, oro al 15, muertes antes del 14, hechizos y runa clave con iconos.
- Al abrir una partida: gráfica de diferencia de oro por minuto, gráfica de CS contra la meta,
  y línea de tiempo de compras (`compras.json`) con iconos y minuto.

Hecho cuando: abrir cualquier partida muestra sus tres bloques sin errores en consola.

**PUNTO DE CONTROL 3.** Detente. Revisión completa del supervisor antes de publicar.

### [x] T10b — Correcciones del punto de control 3

El supervisor revisó las cinco vistas en un navegador real (707 px y 390 px). Sin errores en la
consola. Defectos:

**Muertes (regresión de los retoques de T10):**
1. Con el valor por defecto "Todo el pool" el mapa muestra **0 muertes**. Causa: `matchLookup` en
   `muertes.js` no copia `en_pool`, y el filtro `pool` pregunta `info.en_pool`. Añade `en_pool: p.en_pool`.
   Criterio: por defecto (pool, todos los lados, 0–14) se ven más de 80 puntos.
2. La leyenda (azul victoria / rojo derrota) se añade dentro de `.minimapa` y queda oculta o recortada:
   ponla fuera del mapa, junto a los conteos.
3. El rival en el título del punto sigue con la clave interna: aplica también `nombreCampeon` al rival.

**Partidas:**
4. **La página se desborda en horizontal** (`scrollWidth` 940 px a 707 px de ancho y 879 px a 390 px).
   Envuelve la tabla en un contenedor con `overflow-x: auto`; la página nunca debe pasar del ancho de la ventana.
5. **Celdas de campeón rotas.** Las celdas "Tú" y "Rival" tienen `display: flex` en el `td` (clase
   `.celda-con-icono`), lo que rompe la tabla: el rival aparece debajo del propio y las columnas quedan
   corridas. Pon el flex en un `<div>` dentro del `td`; el `td` sigue siendo `table-cell`.
6. **Panel de detalle invisible al hacer clic.** Aparece al final de la página, 30 filas más abajo. Muéstralo
   justo debajo de la fila pulsada (una fila extra con `colspan`) o haz `scrollIntoView({behavior:"smooth"})`
   al abrirlo. Marca la fila abierta.
7. **Compras sin iconos ni nombres.** La "línea de tiempo" es un scatter de puntos sin significado. Hazla
   en HTML, no en Chart.js: una fila horizontal de iconos de ítem (32 px, `urlItem`) ordenados por minuto,
   cada uno con el minuto debajo ("17.1 min") y el nombre en `title`. Si no hay compras: "Sin compras de
   ítems completos registradas".
8. **Títulos duplicados.** Quita "Últimas partidas" (ya está "Historial de partidas").
9. **A 390 px:** muestra una lista de tarjetas en vez de la tabla (fecha, resultado, retratos, KDA, CS@10,
   Oro@15), o deja la tabla en su contenedor con scroll horizontal; en ambos casos `scrollWidth` = 390.

Hecho cuando (medido en un navegador real; si no hay, dilo y no marques):
- En las cinco vistas, a 1280 px y a 390 px, `document.documentElement.scrollWidth` es igual al ancho de
  la ventana.
- Muertes por defecto muestra más de 80 puntos y la leyenda es visible.
- En Partidas, las columnas "Tú" y "Rival" muestran cada una un retrato y su nombre en la misma fila.
- Al pulsar una partida el detalle se ve sin desplazarse a mano y las compras salen como iconos con minuto.
- `pytest` y `node --test docs/js/calc.test.js` pasan.

**PUNTO DE CONTROL 3 (repetido).** Detente.

### [x] T10c — Restaurar las gráficas del detalle de partida

El supervisor revisó T10b en un navegador real. Corrigió él mismo, sin commit, cuatro defectos pequeños
(inclúyelos tal cual en el commit de esta tarea, no los deshagas):
- `muertes.js`: T10b borró el bloque `matchLookup` y la vista fallaba con
  `ReferenceError: matchLookup is not defined` (0 puntos). Restaurado con `en_pool`.
- `base.css`: `.punto-leyenda` estaba limitado a `.minimapa` y los puntos de la leyenda no se veían.
- `partidas.js`: la fila de detalle se insertaba al final de la tabla; ahora va con `trFila.after(filaDetalle)`.
- `base.css`: `.celda-iconos` y `.celda-runa` tenían `display: flex` en el `td`; ahora son `table-cell`.

Queda un defecto grave, que debes arreglar tú:

1. **T10b borró el código de las dos gráficas del detalle.** Los títulos "Diferencia de oro por minuto" y
   "CS contra la meta" y sus `canvas` siguen, pero no hay ningún `new Chart` en `partidas.js`: los canvas
   quedan vacíos. Recupera ese código del commit de T10 (`git show b896847:docs/js/vistas/partidas.js`,
   los dos bloques `new Chart` de oro y CS) y vuelve a crearlas DESPUÉS de mostrar la fila
   (`filaDetalle.style.display = "table-row"` antes de `new Chart`). Destruye las gráficas anteriores al
   abrir otra partida (`Chart.getChart(canvas)?.destroy()`).
2. **Regla nueva para AGENTS.md:** "Antes de borrar un bloque de código, busca con `grep` dónde se usa. Una
   corrección no puede quitar una función que la tarea no pidió quitar." Añádela a la sección de reglas.

Hecho cuando (medido en un navegador real; si no hay, dilo y no marques):
- Al pulsar tres partidas distintas, una tras otra, cada detalle muestra las dos gráficas con datos y la
  fila de iconos de compras, justo bajo la fila pulsada, sin errores en la consola.
- `Object.keys(Chart.instances).length` no crece al abrir partidas repetidas (se destruyen las anteriores).
- Ninguna vista se desborda en horizontal a 1280 px ni a 390 px (hoy ya se cumple, no lo rompas).
- `pytest` y `node --test docs/js/calc.test.js` pasan.

**PUNTO DE CONTROL 3 (tercer repaso).** Detente.

> **Nota del supervisor para T11:** el árbol de trabajo tiene un último ajuste del supervisor sin commit
> (`partidas.js` y `base.css`: el detalle de partida ocupa el ancho visible aunque la tabla tenga scroll).
> Inclúyelo en el commit de T11. Comprobaciones previas ya hechas por el supervisor: ninguna clave en git
> ni en `docs/`, `.env` y `data/` fuera de git, `docs/` pesa 552 KB. No hay remoto configurado todavía.

### [x] T11 — Publicación en GitHub Pages

- Actualiza `README.md`: cómo ver la página en local y cómo publicar.
- Pasos que hace el usuario (escríbelos en el README, no los ejecutes tú):
  1. Crear un repositorio público en GitHub y agregarlo como remoto `origin`.
  2. `git push -u origin main`.
  3. En el repositorio: Settings → Pages → Source "Deploy from a branch" → rama `main`, carpeta `/docs`.
- Antes del primer push, comprueba que `git ls-files` no incluye `.env` ni nada de `data/`,
  y que `git grep -nE "RGAPI-[0-9a-f]{8}-"` no devuelve nada (este patrón detecta claves reales
  e ignora el marcador de `.env.example`, que usa `x` en lugar de dígitos).

Hecho cuando: el README tiene los pasos y las dos comprobaciones pasan.

### [ ] T12 — Actualización automática con GitHub Actions (falta la ejecución manual en verde)

Desbloqueada: el usuario ya tiene la clave personal de Riot (no expira). Él mismo la guarda como secreto
`RIOT_API_KEY` del repositorio y crea las variables; tú NO pidas, leas ni escribas la clave en ningún archivo.

`.github/workflows/actualizar.yml`:
- Disparadores: `schedule` cada 3 horas (`cron: "17 */3 * * *"`, minuto no redondo) y `workflow_dispatch`.
- `permissions: contents: write` y `concurrency: { group: actualizar, cancel-in-progress: false }`.
- Pasos: `actions/checkout@v4`; `actions/setup-python@v5` con Python 3.12 y caché de pip;
  `pip install -e .`; restaurar `data/` con `actions/cache@v4` (clave con `github.run_id` y
  `restore-keys: prepartida-data-`, para que cada ejecución guarde la base nueva);
  `prepartida init` (si no existe la base), `prepartida estaticos`, `prepartida ingesta --max 200`,
  `prepartida exportar`; commit y push de `docs/data` solo si cambió, con autor
  `github-actions[bot]` y mensaje "Actualizar datos (automático)".
- Entorno del job: `RIOT_API_KEY: ${{ secrets.RIOT_API_KEY }}` y las variables del repositorio
  `RIOT_GAME_NAME`, `RIOT_TAG_LINE`, `RIOT_PLATFORM`, `RIOT_REGION` (`${{ vars.X }}`).
- La clave nunca se imprime: no uses `set -x`, ni `env`, ni `echo` de variables.
- `timeout-minutes: 30`. Si la ingesta falla, el job falla y no hace commit.
- Documenta en el README: dónde ver las ejecuciones (pestaña Actions) y cómo lanzar una a mano.

Hecho cuando: el archivo pasa `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/actualizar.yml'))"`,
`git grep -nE "RGAPI-[0-9a-f]{8}-"` no devuelve nada, y el usuario confirma una ejecución manual en verde
(el supervisor revisa el registro). Hasta esa confirmación, no marques la tarea.

### [x] T13 — Retirar la app de Streamlit

Solo después del punto de control 3 y con aprobación explícita del supervisor:
- borra `src/prepartida/app.py` y el comando `app` de `cli.py`;
- quita `streamlit` de `pyproject.toml`;
- actualiza README y el mapa del repositorio en `AGENTS.md`.

Hecho cuando: `pytest` pasa y `pip install -e ".[dev]"` funciona en un entorno limpio.

## 6. Fase 2 — Referencias por rango (Plata, Oro, Diamante)

Objetivo: comparar las métricas del jugador con las de jugadores reales de LAN de Plata, Oro y
Diamante, en su mismo rol y con exactamente las mismas definiciones. Se hace después de T12 y T13.

Decisiones del supervisor para esta fase:
- Rangos de referencia: `SILVER`, `GOLD`, `DIAMOND`, en la cola `RANKED_SOLO_5x5` de `la1`.
  Bronce no se muestrea: la referencia de Bronce es el propio jugador.
- Roles: `MIDDLE` y `BOTTOM`. De cada partida de la muestra se toman **los dos** jugadores de cada
  uno de esos roles (los dos equipos), porque el emparejamiento los pone en un rango parecido.
- Tamaño: 300 partidas por rango (unas 600 observaciones por rol y rango).
- Solo partidas de los dos últimos parches presentes en la muestra.
- La muestra vive en una base aparte, `data/muestra.duckdb`, con el mismo esquema que
  `data/prepartida.duckdb`. Nunca se mezcla con la base del jugador.
- Privacidad: a `docs/` solo llegan agregados (percentiles y conteos). Ningún PUUID, nombre ni
  identificador de partida de la muestra sale de `data/`.

### [x] R01 — Entradas de liga en el cliente de Riot

- `RiotClient.entradas_de_liga(tier, division, pagina=1) -> list[dict]` llama a
  `GET /lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{division}?page={pagina}` en el enrutamiento de
  plataforma (`la1`). Devuelve la lista tal cual (cada entrada trae `puuid`, `tier`, `rank`, `leaguePoints`).
- `ids_de_partidas` debe aceptar el filtro `queue=420` (Solo/Dúo) y `count`; si ya lo acepta, no lo cambies.
- Pruebas con la API simulada de `tests/conftest.py`: ruta y parámetros correctos, página vacía → lista vacía.

Hecho cuando: `pytest` pasa con las pruebas nuevas.

### [x] R02 — Comando `prepartida muestra`

`src/prepartida/muestra.py` y el comando:

```
prepartida muestra --tier GOLD --partidas 300 [--por-jugador 2] [--semilla 7]
```

1. Recorre las divisiones I a IV del tier. En cada una pide páginas al azar (con la semilla) hasta
   juntar suficientes jugadores; baraja la lista.
2. De cada jugador toma sus `--por-jugador` partidas Solo/Dúo más recientes (`queue=420`).
3. Descarta partidas ya guardadas, de otra cola o de más de 30 días.
4. Descarga partida y timeline y las guarda en `data/muestra.duckdb` reutilizando `guardar_partida`
   de `ingest.py` (sin copia cruda: `raw_dir=None`).
5. Registra en una tabla nueva `muestra_partidas(match_id, tier_muestra, fecha_muestra)` el rango por el
   que entró cada partida. Es la única tabla nueva; se crea en `muestra.py`, no en `db.py`.
6. Se detiene al llegar a `--partidas` partidas del tier. Es reanudable: si se interrumpe y se vuelve a
   ejecutar, sigue donde iba.
7. Muestra progreso cada 25 partidas: "GOLD: 75 de 300 partidas".

Con el límite de 100 peticiones cada 2 minutos, 300 partidas tardan unos 12 minutos por rango.

Pruebas con la API simulada: se detiene en el tope, no duplica partidas, es reanudable, la tabla
`muestra_partidas` queda poblada y no se escribe nada en `data/prepartida.duckdb`.

Hecho cuando: `pytest` pasa. El usuario ejecuta, en su Mac, una muestra corta
(`prepartida muestra --tier GOLD --partidas 20`) y pega la salida en la bitácora. No ejecutes la muestra
completa: la ejecuta el usuario.

### [x] R02b — Correcciones de la muestra

El supervisor revisó R02. La estructura y las pruebas están bien, pero el muestreo no hace lo que pide el plan:

1. **Lee todas las páginas de una división antes de muestrear y llena el cupo solo con División I.**
   `run` pide páginas 1, 2, 3… hasta que una venga vacía (en Oro de LA1 pueden ser decenas de páginas,
   cientos de llamadas) y luego toma jugadores de la División I hasta llegar a 300. La muestra quedaría
   sesgada hacia lo más alto del rango y nunca llegaría a II, III ni IV.
   Arreglo: cupo por división = `ceil(partidas / 4)`. En cada división, pide páginas en orden aleatorio
   (con la semilla) entre 1 y `--max-paginas` (por defecto 10), y deja de pedir páginas cuando tengas
   `cupo * 3` jugadores o una página venga vacía. Si una división no llena su cupo, el sobrante pasa a la
   siguiente.
2. **Descarga partidas viejas para descartarlas después.** Pasa `start_time` (ahora − 30 días, en segundos)
   a `ids_de_partidas` para que la API solo devuelva partidas recientes; mantén la comprobación de fecha.
3. **Guarda partidas sin timeline.** Si `linea_de_tiempo` falla, no guardes ni cuentes esa partida: las
   métricas de la fase 2 necesitan la timeline. Captura solo `RiotError` (no `Exception`).
4. **Un jugador que falla detiene todo.** Si `ids_de_partidas` o `partida` lanzan `NoEncontrado` o
   `RiotError` para un jugador, pasa al siguiente.
5. **Sin resumen final.** Con `--partidas 20` no se imprime nada (el aviso es cada 25). Al terminar,
   imprime siempre: `GOLD: 20 de 20 partidas (I: 5, II: 5, III: 5, IV: 5)`.
6. **Ruta fija.** Usa `cfg.data_dir / "muestra.duckdb"` en vez de `Path("data")`.

Pruebas nuevas: reparto entre las cuatro divisiones, `start_time` presente en la llamada, partida con
timeline fallida no se guarda, jugador con error se salta, resumen final impreso.

Hecho cuando: `pytest` pasa y el usuario ejecuta en su Mac `prepartida muestra --tier GOLD --partidas 20`
y la salida (el resumen final) queda en la bitácora. Entonces se marcan R02 y R02b.

### [ ] R03 — Métricas para cualquier participante

> Nota del supervisor (tras R02b): la muestra GOLD tiene 15 de 300 partidas de menos de 15 minutos (remakes y rendiciones; la más corta dura 67 s). `metricas_por_rol` debe excluir partidas de menos de 15 minutos de las métricas a los 15 (dif_oro_15, muertes_14) y las de menos de 5 minutos de todo; agrega una prueba para cada caso.

Hoy `partidas_del_jugador` calcula las métricas de línea solo para un PUUID. Hace falta lo mismo para
todos los participantes de un rol.

- En `metricas.py`, nueva función `metricas_por_rol(con, posiciones=("MIDDLE","BOTTOM")) -> DataFrame`:
  una fila por participante y partida con `match_id`, `posicion`, `campeon`, `victoria`, `cs_10`,
  `dif_oro_10`, `dif_oro_15`, `muertes_14`, `parche`, y el `tier_muestra` si la tabla existe.
  Usa la misma consulta de rival de posición que `SQL_PARTIDAS`: no inventes otra definición.
- **Prueba de regresión obligatoria:** sobre la base de pruebas, las filas del jugador que devuelve
  `metricas_por_rol` coinciden exactamente con las de `partidas_del_jugador` en esas cinco métricas.
- No cambies `partidas_del_jugador`.

Hecho cuando: `pytest` pasa, incluida la prueba de regresión.

### [ ] R04 — Exportar `referencias.json`

Nueva sección 3.8 del contrato de datos (aprobada por el supervisor; agrégala a la sección 3):

```json
{
  "generado": "2026-11-20T15:00:00Z",
  "parches": ["26.22", "26.23"],
  "rangos": {
    "GOLD": {
      "partidas": 300,
      "MIDDLE": {
        "observaciones": 598,
        "cs_10":      {"p25": 61.0, "p50": 68.0, "p75": 75.0},
        "dif_oro_10": {"p25": -310, "p50": 0, "p75": 300},
        "dif_oro_15": {"p25": -620, "p50": 0, "p75": 610},
        "muertes_14": {"p25": 0, "p50": 1, "p75": 2},
        "por_muertes_14": [
          {"muertes": "0", "partidas": 210, "tasa": 58.1},
          {"muertes": "1", "partidas": 190, "tasa": 49.5},
          {"muertes": "2+", "partidas": 198, "tasa": 41.2}
        ],
        "curva_cs": [0, 0, 4, 11, ...]
      },
      "BOTTOM": { ... }
    },
    "SILVER": { ... },
    "DIAMOND": { ... }
  }
}
```

- Las cifras del ejemplo son de relleno: las reales salen de la muestra.
- `curva_cs`: mediana del CS acumulado por minuto, del 0 al 20 (21 valores).
- Los percentiles de `dif_oro_10` y `dif_oro_15` son simétricos por construcción (cada partida aporta
  las dos caras de la línea). Esto es esperado: lo útil es el p75 y la dispersión.
- Un rango o rol con menos de 100 observaciones se exporta con `"muestra_pequena": true`.
- `prepartida exportar` escribe `referencias.json` solo si existe `data/muestra.duckdb`; si no, no lo crea.
- Prueba de privacidad: el JSON exportado no contiene ningún PUUID ni `match_id` de la base de pruebas.

Hecho cuando: `pytest` pasa y `docs/data/referencias.json` cumple el contrato con la muestra corta de R02.

### [ ] R05 — Referencias en la página

Solo vistas; los cálculos van en `calc.js` con pruebas.

1. **Inicio.** Bajo cada uno de los cuatro indicadores (CS al 10, oro al 15, muertes antes del 14 y,
   para la tasa, nada), una regla horizontal con tres marcas de la mediana (Plata, Oro, Diamante) y un
   punto con el valor del jugador. Texto: "Mediana en Oro: 68.0 · te faltan 13.0". El rol de referencia
   es `perfil.roles.principal`.
2. **Bloque "Tu brecha más grande frente a Oro".** Para cada métrica, la distancia del jugador a la
   mediana de Oro medida en rangos intercuartílicos ((Oro p50 − tú) / (Oro p75 − Oro p25)). Se muestra
   la métrica con la mayor distancia desfavorable, con su texto. Es la prioridad de entrenamiento.
3. **Línea.** En la gráfica de CS acumulado, una línea discontinua con la `curva_cs` de Oro del rol
   seleccionado. Leyenda "Mediana en Oro".
4. Si `referencias.json` no existe, nada de lo anterior se muestra y la página funciona igual.
5. Cada referencia muestra su número de observaciones y "muestra pequeña" cuando corresponde.

Hecho cuando (navegador real; si no hay, dilo y no marques): las reglas de referencia se ven en Inicio a
1280 y 390 px sin desbordar; la línea de Oro aparece en Línea; quitando `referencias.json` la página
carga sin errores; `node --test docs/js/calc.test.js` y `pytest` pasan.

**PUNTO DE CONTROL 4.** Detente. El supervisor revisa los números contra la muestra y la página.

### [ ] R06 — Actualización semanal de las referencias

- `.github/workflows/referencias.yml`: `schedule` semanal (lunes, minuto no redondo) y `workflow_dispatch`.
- Restaura y guarda `data/muestra.duckdb` con `actions/cache@v4` (clave con `github.run_id`,
  `restore-keys: prepartida-muestra-`).
- Ejecuta `prepartida muestra` para SILVER, GOLD y DIAMOND con `--partidas 300`, luego
  `prepartida exportar`, y hace commit de `docs/data/referencias.json` si cambió.
- Mismo `concurrency: { group: actualizar }` que el flujo de T12, para que nunca corran a la vez y
  compartan bien el límite de la clave.
- Para que la muestra siga fresca, `muestra` descarta del cálculo las partidas de más de 30 días (no
  las borra de la base).
- `timeout-minutes: 90`.

Hecho cuando: el YAML es válido, no hay claves en git y el usuario confirma una ejecución manual en verde.

## 7. Fase 3 — Asistente de draft (antes de la partida)

Objetivo: con la selección de campeones (5 aliados, 5 enemigos, roles y lado del mapa), producir antes
de jugar: qué campeón del pool elegir y por qué, runas y hechizos, ruta de ítems para esa partida y el
plan de juego (línea, mapa, objetivos y condición de victoria). No predice el resultado: nunca muestres
una probabilidad de ganar.

Decisiones del supervisor para esta fase:
- **Aplicación local**, no en GitHub Pages: la clave de NVIDIA NIM no puede vivir en una página pública,
  y la lectura automática del draft (fase 3c) solo funciona en el Mac del jugador.
  Servidor en Python en `http://127.0.0.1:8765`, solo en la interfaz local (nunca `0.0.0.0`).
  Interfaz en `asistente/` (HTML, CSS y módulos ES, sin framework), reutilizando `docs/css/tokens.css`.
  `asistente/` no se publica.
- **Dependencias aprobadas para esta fase:** `fastapi` y `uvicorn` (servidor local). Nada más. Las
  llamadas a NIM se hacen con `httpx`, que ya está instalado. No agregues el paquete `openai`.
- **Sin scraping de páginas de terceros.** Para estadísticas de matchups, el asistente muestra enlaces
  a la página del matchup (por ejemplo `https://lolalytics.com/lol/<campeon>/vs/<rival>/build/`, con las
  claves en minúscula); el jugador los consulta él mismo.
- **El modelo de lenguaje solo redacta.** Todo dato (cifras, ítems, runas, tiempos) sale de las capas
  de conocimiento. El modelo convierte una lista de hechos en texto y no puede añadir hechos.
- **Dos versiones del briefing:** corta (máximo 5 líneas, para leer durante la selección) y larga
  (para la pantalla de carga).

### [ ] D01 — Ficha automática de campeones

`src/prepartida/conocimiento.py` y el comando `prepartida conocimiento --generar`, que escribe
`conocimiento/campeones.toml` con una entrada por campeón, calculada solo de Data Dragon:

```toml
[Ahri]
dano = "magico"        # "fisico", "magico" o "mixto", de info.attack frente a info.magic
alcance = "distancia"  # "cuerpo" si stats.attackrange <= 300, si no "distancia"
etiquetas_riot = ["Mage", "Assassin"]
# Campos curados (D02): vacíos aquí
enganche = ""
control = ""
escala = ""
arquetipo = ""
verificado = false
```

- Regla para `dano`: "magico" si `info.magic >= info.attack + 3`; "fisico" si `info.attack >= info.magic + 3`;
  si no, "mixto". Es una aproximación y se anota así en el archivo.
- Volver a generar **no borra** los campos curados ni `verificado` de las entradas existentes.

Hecho cuando: `pytest` pasa (incluida la prueba de que regenerar conserva lo curado) y el archivo tiene
todos los campeones de `estaticos`.

### [ ] D02 — Borrador de los campos curados con NIM

Los campos `enganche` (0–3), `control` (0–3), `escala` ("temprano", "medio", "tardio") y `arquetipo`
(uno de: "asesino", "mago_control", "mago_poke", "tirador", "tanque", "luchador", "encantador",
"desplazador") no salen de Data Dragon.

- `prepartida conocimiento --borrador --top 60` toma los 60 campeones más frecuentes en
  `data/muestra.duckdb` (más los del pool), pide a NIM un borrador de esos cuatro campos para cada uno
  y lo escribe con `verificado = false` y `fuente = "borrador NIM"`. No toca entradas con `verificado = true`.
- Variables en `.env`: `NIM_API_KEY` y `NIM_MODELO` (el usuario elige el modelo en build.nvidia.com).
  Base: `https://integrate.api.nvidia.com/v1/chat/completions`. Respuesta pedida en JSON y validada:
  un valor fuera de las opciones se descarta y el campo queda vacío.
- Pausa entre llamadas para no pasar de 30 por minuto.
- El jugador y el supervisor revisan el borrador y marcan `verificado = true` a mano. El motor de D03
  solo usa campos de entradas verificadas; los demás cuentan como desconocidos.

Hecho cuando: `pytest` pasa con NIM simulado (incluida la validación de valores) y la bitácora dice
cuántos campeones quedaron con borrador. **Detente:** el usuario revisa el borrador antes de D03.

### [ ] D03 — Perfil de una composición

`src/prepartida/composicion.py`, funciones puras con pruebas:

- `perfil_equipo(campeones: list[str], fichas) -> dict` con: proporción de daño físico y mágico,
  enganche total, control total, escala dominante, arquetipos presentes, número de campeones cuerpo a
  cuerpo, y `desconocidos` (campeones sin ficha verificada).
- `contraste(aliado, enemigo) -> dict` con las diferencias: quién tiene más enganche, quién escala
  mejor, si el enemigo es casi todo de un tipo de daño (≥ 70 %).
- Las pruebas usan fichas inventadas en el propio test, no `conocimiento/campeones.toml`.

Hecho cuando: `pytest` pasa.

### [ ] D04 — Reglas del briefing y puntuación del pool

1. `reglas/briefing.toml` con reglas declarativas `condicion → hecho`. El supervisor escribe el primer
   lote de reglas (no las inventes): la tarea es el **intérprete**. Formato:

```toml
[[regla]]
id = "enemigo_fisico"
si = "enemigo.prop_fisico >= 0.7"
hecho = "El equipo enemigo hace casi todo su daño físico: prioriza armadura en tu primer ítem defensivo."
categoria = "compras"
```

   El intérprete evalúa solo comparaciones simples sobre los campos de `perfil_equipo` y `contraste`
   (`>=`, `<=`, `==`, `and`). No uses `eval`.
2. `puntuar_pool(seleccion, historial, fichas) -> list[dict]`: una fila por campeón del pool jugable en
   el rol del jugador, con una puntuación que es la **suma explicada** de componentes, cada uno con su
   texto y su número de partidas:
   - tu tasa ajustada con ese campeón en ese rol (la de `metricas.tasa_ajustada`);
   - tu historial contra el arquetipo del rival de línea;
   - encaje con tu equipo (por ejemplo, tu equipo ya tiene 4 de daño físico y tu campeón hace daño mágico).
   Los pesos van en `reglas/briefing.toml`, no en el código.
3. Las runas, hechizos e ítems sugeridos salen de dos fuentes, cada una con su número de partidas:
   tus propias partidas con ese campeón, y la muestra de Oro y Diamante (`muestra.duckdb`). Si hay
   menos de 10, se muestra "muestra pequeña" y el enlace a la página del campeón.

Hecho cuando: `pytest` pasa con un caso completo de selección inventado en el test.

### [ ] D05 — Servidor local y entrada del draft

- `prepartida asistente` levanta FastAPI en `127.0.0.1:8765` y abre el navegador.
- Página `asistente/index.html`: dos columnas de 5 casillas (aliados y enemigos) con autocompletado
  de nombres de campeón, selector de rol de cada uno, tu posición, lado (azul o rojo) y botón
  "Preparar partida". Retratos de Data Dragon como en la página publicada.
- `POST /api/briefing` recibe la selección y devuelve los hechos estructurados (D03 y D04), sin modelo
  de lenguaje todavía. La página los muestra en secciones: Pick, Runas y hechizos, Compras, Línea,
  Mapa y objetivos, Condición de victoria, Enlaces de matchup.
- Los campeones aún no elegidos pueden quedar vacíos: el briefing se calcula con lo que haya.

Hecho cuando (navegador real; si no hay, dilo y no marques): con una selección de prueba la página muestra
las secciones sin errores en la consola, y con dos casillas enemigas vacías también funciona.

### [ ] D06 — Redacción del briefing con NIM

- `src/prepartida/redaccion.py`: recibe los hechos de D05 y pide a NIM dos textos (corto: máximo 5
  líneas; largo: máximo 250 palabras), en español, en segunda persona.
- El prompt incluye solo los hechos y la instrucción de no añadir cifras, ítems, runas ni tiempos que no
  estén en ellos.
- **Validación:** cada número que aparezca en el texto debe estar en los hechos; si no, se descarta el
  texto y se muestran los hechos en viñetas. Lo mismo si NIM falla o tarda más de 15 s.
- Caché por hash de los hechos, en `data/briefings/`.
- La página muestra primero el corto y debajo "Ver plan completo".

Hecho cuando: `pytest` pasa con NIM simulado (incluido un texto con una cifra inventada, que debe
descartarse) y la bitácora incluye un briefing real generado por el usuario.

**PUNTO DE CONTROL 5.** Detente. El supervisor y el jugador prueban el asistente con 5 drafts de partidas
ya jugadas y comparan el plan con lo que pasó.

### Fase 3b y 3c (no ejecutar todavía)

- **3b — Conocimiento curado:** verificar `reglas/objetivos.toml` contra notas de parche oficiales;
  incorporar la recopilación de xPeke como reglas y hechos con su fuente.
- **3c — Automatización:** leer el draft en vivo desde el cliente con la API local del cliente (LCU,
  ruta `/lol-champ-select/v1/session`; no oficial, puede cambiar con cada parche); decidir si se usan
  estadísticas de terceros.
- **Medición:** comparar muertes antes del 14 y oro al 15 antes y después de usar el asistente.

## 8. Fases posteriores (no ejecutar)

- Magos en la línea inferior, panel de ítems en vivo, otros roles; jungla al final.

## 9. Decisiones ya tomadas

- La página es pública. Por eso el contrato de datos excluye identificadores de otros jugadores.
- Sin framework ni compilación en la página: HTML, CSS y módulos ES.
- Chart.js 4 es la única librería de terceros en la página, en copia local.
- La clave de Riot vive en `.env` en local. Cuando exista la clave personal, además como secreto de GitHub.
- La carpeta publicada es `docs/` porque GitHub Pages solo admite la raíz o `/docs` al publicar desde una rama.
- Fase 2: la muestra de referencia vive en `data/muestra.duckdb` y solo se publican agregados.
- Fase 3: el asistente de draft es una aplicación local (127.0.0.1); el modelo de lenguaje solo redacta
  hechos calculados; sin scraping de páginas de terceros.
