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
