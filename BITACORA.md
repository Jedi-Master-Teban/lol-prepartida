# BITACORA

## T01 — 2026-11-16
- Archivos: `.gitignore`, `BITACORA.md`, `PLAN.md` y todo lo versionable del proyecto
  (`src/prepartida/`, `tests/`, `README.md`, `perfil.toml`, `pyproject.toml`, `reglas/`, `AGENTS.md`)
- Verificación: `git status` limpio; `git ls-files | grep -E "^\.env$|^data/|^\.venv/"` no devuelve nada;
  `pytest` pasa
- Decisiones tomadas:
  - `git init -b main` en la raíz del proyecto. La carpeta está dentro de otro repositorio
    (`/Users/estebanarriaga/Código`), así que quedó un repositorio anidado: el repositorio padre
    la ve como carpeta sin versionar.
  - `.gitignore` ya tenía `.env`, `data/` y `.venv/`; se agregaron `.DS_Store` y `node_modules/`.
  - Un solo commit por tarea, con el marcado del plan y esta entrada incluidos, según el flujo de
    `AGENTS.md`. `BITACORA.md` se creó primero solo con el título.
  - `.env.example` conserva el marcador `RGAPI-xxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`: es una plantilla,
    no una clave real.
- Dudas para el supervisor: en T11 la comprobación `git grep -n "RGAPI-"` devuelve la línea del
  marcador en `.env.example` (y la mención dentro de `PLAN.md`). Decide si en T11 se cambia el
  marcador de `.env.example` o se ajusta la comprobación.

## Revisión del supervisor — T01 — 2026-11-16
- T01 aprobada. Sin correcciones al trabajo.
- Duda resuelta: la comprobación de T11 era un error del plan. Se cambió en `PLAN.md` a
  `git grep -nE "RGAPI-[0-9a-f]{8}-"`. No se toca `.env.example`.
- Repositorio anidado dentro de `Código`: aceptado. No se modifica el repositorio padre.
- El cambio de `PLAN.md` y esta entrada quedan sin commit: inclúyelos en el commit de T02.

## T02 — 2026-11-16
- Archivos: `src/prepartida/exportar.py` (nuevo), `tests/test_exportar.py` (nuevo),
  `src/prepartida/metricas.py` (columnas nuevas en `SQL_PARTIDAS`), `PLAN.md`, `BITACORA.md`
- Verificación: `pytest` (26 pasan, 10 nuevos); con la base real: 77 partidas, 77 curvas,
  496 muertes, 204 compras, 171 elementos estáticos; ningún JSON contiene el PUUID, `otro-` ni `NaN`
- Decisiones tomadas:
  - `SQL_PARTIDAS` solo se amplió (nuevas columnas al final del `SELECT`): `champion_id`,
    `rival_champion_id`, `item0`–`item6`, `hechizo1`, `hechizo2`, `runa_clave`, `arbol_primario`,
    `arbol_secundario`. Las columnas existentes no se tocaron.
  - El rival de posición es el participante con la misma posición en el lado contrario. Si el jugador
    no tiene posición, no hay rival y `dif_oro` va en `null` en todos los minutos.
  - Las curvas se cortan en el minuto 40 (41 valores, índices 0 a 40). Hay dos partidas reales sin
    cuadros del minuto 10: su `cs_10` va en `null`.
  - `compras.json` solo incluye partidas con al menos una compra de ítem completo (oro >= 2200);
    las partidas sin compras no aparecen.
  - Los JSON se escriben con `indent=2` y `allow_nan=False`: si un `NaN` se colara, el exportador
    falla en vez de escribirlo. `NaN` y `NaT` se convierten en `null`.
  - `version_ddragon` es la versión más reciente de `campeones.version`, comparada por partes
    numéricas (`16.22.1` > `16.9.1`). Si la tabla `campeones` está vacía, se usa la carpeta más
    nueva de `data/estaticos/`.
  - Los datos de runas y hechizos se leen de `data/estaticos/<version>/runesReforged.json` y
    `summoner.json`. Los hechizos se indexan por el campo `key` (texto), como pide el contrato.
  - `estaticos.json` incluye solo lo referenciado por el resto de archivos: 56 campeones, 92 ítems,
    11 runas, 5 árboles y 7 hechizos.
- Dudas para el supervisor:
  - `compras.json`: ahora no incluye las partidas sin compras. Si la vista de partidas necesita la
    lista completa, se cambia para dejar `[]` en cada partida.
  - En `partidas.json`, `hechizos` es un arreglo de dos posiciones: si falta un hechizo queda `null`
    dentro del arreglo. No pasa con los datos reales.

## T03 — 2026-11-16
- Archivos: `src/prepartida/cli.py` (comandos `exportar` y `publicar`), `tests/test_cli.py` (nuevo),
  `docs/data/*.json` (los seis archivos con datos reales), `.gitignore`, `PLAN.md`, `BITACORA.md`
- Verificación: `pytest` (30 pasan, 4 nuevos); `prepartida exportar` genera los seis archivos con la
  base real (77 partidas, 77 curvas, 496 muertes, 204 compras, 171 estáticos); `prepartida publicar`
  con una clave falsa muestra el error y no continúa
- Decisiones tomadas:
  - `exportar` abre la base en solo lectura con `duckdb.connect(..., read_only=True)`; `db.py` no se
    tocó. Si la base no existe, avisa y devuelve 2.
  - `exportar` y `publicar` aceptan `--destino` (por defecto `docs/data`) y `--perfil`
    (por defecto `perfil.toml`).
  - `publicar` hace ingesta, exportación, `git add`, commit y push. Si los datos no cambiaron, lo
    dice y no hace commit ni push. Si no hay remoto configurado, hace el commit y avisa que omite
    el push.
  - Los comandos de git se ejecutan en la raíz del repositorio (`git rev-parse --show-toplevel`),
    así que el comando funciona desde cualquier subcarpeta.
  - El mensaje del commit de datos es `datos: <fecha> <hora>` en hora local, por ejemplo
    `datos: 2026-11-16 16:20`.
  - `.gitignore`: el patrón `data/` ignoraba también `docs/data/`, que sí se versiona (es lo que se
    publica). Se cambió a `/data/`, que sigue ignorando la base local y las respuestas crudas.
  - Con clave inválida, `publicar` captura `ClaveInvalida`, escribe `La ingesta falló: ...` y
    devuelve 1 sin exportar ni hacer commit.
- Dudas para el supervisor: el formato del commit de datos (`datos: <fecha> <hora>`) fue decisión
  mía; se puede cambiar a solo fecha si se prefiere.

## Revisión del supervisor — punto de control 1 (T02 y T03) — 2026-11-16
- T02 y T03 aprobadas con dos correcciones, descritas en la tarea nueva **T03b** de `PLAN.md`.
  Hazla antes de T04.
- Verificado por el supervisor contra la base real: 30 pruebas pasan; los seis JSON cumplen el
  contrato; ningún PUUID ni `NaN`; `curvas` coincide con `partidas` en `cs_10` y `dif_oro_15`
  en las 77 partidas; 496 muertes = suma de `muertes`; resumen: CS al 10 = 55.0, oro al 15 = −414,
  por detrás en 47 de 74, muertes antes del 14 = 1.52.
- Dudas resueltas:
  - `compras.json` sin las partidas sin compras: se queda así. Quedó escrito en el contrato (3.5).
  - `hechizos` con `null` dentro del arreglo: aceptado.
  - Mensaje del commit de datos `datos: <fecha> <hora>`: aceptado.
  - Cambio de `.gitignore` a `/data/`: correcto; era un error del plan.
- Nota para T09: `muertes[].minuto` está redondeado a 1 decimal. Para contar muertes antes del
  minuto 14 usa `partidas[].muertes_14`, no el filtro sobre `minuto`.
- El cambio de `PLAN.md` y esta entrada quedan sin commit: inclúyelos en el commit de T03b.

## T03b — 2026-11-16
- Archivos: `src/prepartida/exportar.py`, `src/prepartida/cli.py`,
  `tests/test_exportar.py`, `tests/test_cli.py`, `PLAN.md`, `BITACORA.md`
- Verificación: `pytest` (32 pasan, 2 nuevos); `node --test` (16 pasan); tras `prepartida exportar`
  con la base real, todo `item_id` de `compras.json` y de `partidas[].items` existe en
  `estaticos.items` (93 ítems, 0 faltantes)
- Decisiones tomadas:
  - `_estaticos` une los ítems de `partidas[].items` con los `item_id` de todas las compras de
    `compras.json`, así un ítem comprado que nunca quedó en el inventario final de una partida
    (p. ej. `3003`, 12 compras reales) sí aparece en `estaticos.items`.
  - `_publicar_en_git` limita el commit a la carpeta de datos:
    `git commit -m <mensaje> -- <destino>`. Un archivo ajeno preparado con `git add` antes de
    publicar no entra en el commit de datos.
- Dudas para el supervisor: ninguna.

## T04 — 2026-11-16
- Archivos: `docs/.nojekyll`, `docs/index.html`, `docs/css/tokens.css`, `docs/css/base.css`,
  `docs/js/main.js`, `docs/js/datos.js`, `docs/js/imagenes.js`,
  `docs/js/vistas/{inicio,pool,linea,muertes,partidas}.js` (vacías, se rellenan en T06-T10),
  `docs/vendor/chart.umd.js`
- Verificación: `python -m http.server 8001 -d docs` sirve la cabecera con datos reales y las cinco
  pestañas cambian de sección; todos los recursos (CSS, JS, Chart.js, JSON) devuelven 200;
  `pytest` (30 pasan) y `node --test` (16 pasan) en verde
- Decisiones tomadas:
  - Chart.js 4.4.1 descargado de la distribución oficial en `docs/vendor/chart.umd.js` (el plan lo
    ubica bajo `docs/`).
  - Todas las rutas son relativas (`data/*.json`, `css/`, `js/`, `vendor/`) para GitHub Pages en
    subcarpeta.
  - `main.js` importa las vistas y orquesta el renderizado: cada vista expone `render(container,
    datos)`; la navegación usa el fragmento de URL (`#inicio`, `#pool`, `#linea`, `#muertes`,
    `#partidas`) y `window.addEventListener('hashchange')`.
  - Las vistas están vacías en T04; `main.js` solo las renderiza si exportan `render`.
- Dudas para el supervisor: ninguna.

## T05 — 2026-11-16
- Archivos: `docs/js/calc.js`, `docs/js/calc.test.js`
- Verificación: `node --test` (16 pasan); pruebas mínimas: `tasaAjustada(2,3)` redondeado a 1 decimal
  = `53.8`, `tasaAjustada(0,0)` = `50`; `agrupar` con 3 partidas (2 victorias) da `tasa` 66.7;
  los promedios ignoran `null`; `aCoordenadaMapa(0,0)` da `{ izquierda: 0, arriba: 100 }`
- Decisiones tomadas:
  - Funciones puras, sin acceso al DOM, exportadas como módulos ES.
  - Las funciones leen las claves en `snake_case` del contrato (cs_10, dif_oro_15, muertes_14,
    victoria) y devuelven claves en `camelCase` (cs10, difOro15, muertes14) para la vista.
  - `promedio` devuelve `null` cuando no hay datos válidos; `tendencia` es una media móvil trailing
    de `ventana` partidas; `curvaPromedio` promedia por minuto entre las partidas indicadas,
    cubriendo minutos 0 a `hastaMinuto` (por defecto 20).
- Dudas para el supervisor: ninguna.
