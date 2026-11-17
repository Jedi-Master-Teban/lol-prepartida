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

### [ ] T07 — Vista Pool

`docs/js/vistas/pool.js`:
- Una tarjeta por combinación campeón–posición del pool, ordenadas por partidas.
- Cada tarjeta: retrato, nombre, posición, partidas, victorias, tasa ajustada, CS al 10,
  oro al 15 y muertes antes del 14. Etiqueta "muestra pequeña" con menos de 10 partidas.
- Indicador de línea: barra horizontal centrada en cero con el oro al 15 (a favor en `--victoria`,
  en contra en `--derrota`), con el número escrito.
- Sección plegable "Fuera del pool" con las mismas tarjetas en tamaño reducido.

Hecho cuando: las cifras de Ahri MIDDLE coinciden con `prepartida estado`.

### [ ] T08 — Vista Línea

`docs/js/vistas/linea.js`:
- Selector de campeón (pool) y de posición.
- **Diferencia de oro frente al rival, minuto 0 a 20:** línea promedio de las partidas seleccionadas,
  línea de cero marcada y área sombreada a favor o en contra.
- **CS acumulado, minuto 0 a 20:** línea promedio y línea de meta recta de 0 a `meta_cs_10` en el minuto 10,
  prolongada con la misma pendiente.
- **Según muertes tempranas:** tres barras (0, 1, 2 o más muertes antes del 14) con tasa, partidas
  y oro medio al 15.

Hecho cuando: cambiar el selector actualiza las tres gráficas y cada una indica cuántas partidas promedia.

### [ ] T09 — Vista Muertes

`docs/js/vistas/muertes.js`:
- Minimapa cuadrado con las muertes como puntos, posicionadas con `aCoordenadaMapa`.
- Filtros: campeón, lado (azul o rojo), tramo de tiempo (0–14, 14–25, 25 en adelante). Por defecto 0–14.
- Al pasar sobre un punto: campeón, rival, minuto y resultado.
- Conteo visible de muertes mostradas y de partidas.

**Verificación obligatoria de coordenadas:** las muertes de un jugador de mid antes del minuto 10
deben caer en su mayoría sobre la diagonal central del mapa. Si aparecen desplazadas o reflejadas,
detente y anótalo: no ajustes los límites a ojo.

Hecho cuando: los filtros funcionan y la verificación de coordenadas se cumple.

### [ ] T10 — Vista Partidas

`docs/js/vistas/partidas.js`:
- Lista de las últimas 30 partidas, de la más reciente a la más antigua: fecha local, resultado
  (texto y color), retrato propio, retrato del rival, posición, lado, KDA (asesinatos/muertes/asistencias),
  CS al 10, oro al 15, muertes antes del 14, hechizos y runa clave con iconos.
- Al abrir una partida: gráfica de diferencia de oro por minuto, gráfica de CS contra la meta,
  y línea de tiempo de compras (`compras.json`) con iconos y minuto.

Hecho cuando: abrir cualquier partida muestra sus tres bloques sin errores en consola.

**PUNTO DE CONTROL 3.** Detente. Revisión completa del supervisor antes de publicar.

### [ ] T11 — Publicación en GitHub Pages

- Actualiza `README.md`: cómo ver la página en local y cómo publicar.
- Pasos que hace el usuario (escríbelos en el README, no los ejecutes tú):
  1. Crear un repositorio público en GitHub y agregarlo como remoto `origin`.
  2. `git push -u origin main`.
  3. En el repositorio: Settings → Pages → Source "Deploy from a branch" → rama `main`, carpeta `/docs`.
- Antes del primer push, comprueba que `git ls-files` no incluye `.env` ni nada de `data/`,
  y que `git grep -nE "RGAPI-[0-9a-f]{8}-"` no devuelve nada (este patrón detecta claves reales
  e ignora el marcador de `.env.example`, que usa `x` en lugar de dígitos).

Hecho cuando: el README tiene los pasos y las dos comprobaciones pasan.

### [ ] T12 — Actualización automática con GitHub Actions — BLOQUEADA

Bloqueada hasta que el usuario tenga la clave personal de Riot (no expira) y la guarde como
secreto `RIOT_API_KEY` del repositorio. La clave de desarrollo expira cada 24 horas y no sirve.

Especificación para cuando se desbloquee:
- `.github/workflows/actualizar.yml`, con `schedule` cada 3 horas y `workflow_dispatch`.
- Pasos: instalar Python 3.12, `pip install -e .`, restaurar `data/` con `actions/cache`,
  `prepartida estaticos`, `prepartida ingesta`, `prepartida exportar`, y commit de `docs/data` si cambió.
- Variables de cuenta (`RIOT_GAME_NAME`, `RIOT_TAG_LINE`, `RIOT_PLATFORM`, `RIOT_REGION`) como
  variables del repositorio, no como secretos.
- La clave nunca se imprime en los registros.

### [ ] T13 — Retirar la app de Streamlit

Solo después del punto de control 3 y con aprobación explícita del supervisor:
- borra `src/prepartida/app.py` y el comando `app` de `cli.py`;
- quita `streamlit` de `pyproject.toml`;
- actualiza README y el mapa del repositorio en `AGENTS.md`.

Hecho cuando: `pytest` pasa y `pip install -e ".[dev]"` funciona en un entorno limpio.

## 6. Fases posteriores (no ejecutar)

Están aquí para dar contexto. No tienen tareas porque falta la especificación.

- **Fase 2 — Motor de reglas y base de conocimiento (mid).** Etiquetas por campeón, clasificación
  de composiciones y reglas que derivan la condición de victoria, la postura en línea y la prioridad
  de objetivos. Falta: taxonomía de etiquetas, reglas concretas y fuente del contenido de matchups.
- **Fase 3 — Briefing y hoja de compras.** Entrada manual de champ select en la página; plan por
  composición calculado en el navegador; textos por matchup precalculados con un modelo de lenguaje.
- **Fase 4 — Estadísticas de LAN Bronce–Oro y baneos.** Muestreo de partidas y cifras de terceros.
- **Fase 5 — Extensiones.** Magos en bot, panel de ítems en vivo, otros roles; jungla al final.

## 7. Decisiones ya tomadas

- La página es pública. Por eso el contrato de datos excluye identificadores de otros jugadores.
- Sin framework ni compilación en la página: HTML, CSS y módulos ES.
- Chart.js 4 es la única librería de terceros en la página, en copia local.
- La clave de Riot vive en `.env` en local. Cuando exista la clave personal, además como secreto de GitHub.
- La carpeta publicada es `docs/` porque GitHub Pages solo admite la raíz o `/docs` al publicar desde una rama.
