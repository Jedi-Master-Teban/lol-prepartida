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
