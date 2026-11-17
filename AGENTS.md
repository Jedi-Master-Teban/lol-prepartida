# AGENTS.md — lol-prepartida

Instrucciones para cualquier agente de código que trabaje en este repositorio.
Lee este archivo completo y después `PLAN.md` antes de tocar nada.

## Qué es el proyecto

Herramienta personal de preparación pre-partida para League of Legends (SoloQ).
Un proceso en Python descarga las partidas del jugador desde la API de Riot, las guarda
en una base local DuckDB y exporta archivos JSON. Una página web estática en `docs/`
lee esos JSON y muestra métricas y gráficas. La página se publica con GitHub Pages.

No es un predictor de victoria. Nunca muestres "probabilidad de ganar".

## Cómo trabajar

1. Abre `PLAN.md` y toma **la primera tarea sin marcar** cuyo estado no sea BLOQUEADA.
2. Haz **una sola tarea por sesión**. No adelantes trabajo de otras tareas.
3. Cumple todos los puntos de "Hecho cuando" de la tarea. Si no puedes cumplir uno, detente.
4. Ejecuta las verificaciones (sección "Comandos"). Todas deben pasar.
   Un "Hecho cuando" visual ("se ve bien") solo se da por cumplido si lo comprobaste en un
   navegador real y anotaste en la bitácora las medidas que pide la tarea. Si no puedes abrir un
   navegador, dilo en la bitácora en vez de darlo por cumplido.
5. Marca la tarea con `[x]` en `PLAN.md` y agrega una entrada al final de `BITACORA.md`.
6. Haz un commit por tarea: `T05: funciones de cálculo y pruebas`.
   El commit de una tarea contiene el código de esa tarea y nada de tareas posteriores.
   Respeta el orden del plan: no empieces una tarea si hay una anterior sin marcar.
7. Si la tarea termina en un **PUNTO DE CONTROL**, detente y avisa al usuario: el supervisor revisa antes de seguir.

### Formato de la entrada en BITACORA.md

```
## T05 — 2026-11-20
- Archivos: docs/js/calc.js, docs/js/calc.test.js
- Verificación: pytest (22 pasan), node --test (9 pasan)
- Decisiones tomadas: (lo que no estaba en el plan y tuviste que decidir)
- Dudas para el supervisor: (o "ninguna")
```

## Cuándo detenerte y preguntar

Detente, no improvises, y escribe la duda en `BITACORA.md` si:

- el plan contradice el código existente;
- un "Hecho cuando" no se puede cumplir;
- necesitas una dependencia nueva;
- necesitas cambiar el contrato de datos (sección 3 de `PLAN.md`);
- una prueba existente falla y no sabes por qué;
- la tarea está marcada BLOQUEADA.

## Reglas que no se rompen

- **Secretos:** nunca leas en voz alta, imprimas, copies ni subas el contenido de `.env`.
  Nunca escribas una clave en código, pruebas, bitácora ni commits.
- **Git:** `.env`, `data/` y `.venv/` no se versionan. Antes de cada commit revisa `git status`.
  No uses `git push --force`. No reescribas historial.
- **Privacidad:** los JSON de `docs/data/` son públicos. Nunca exportes PUUID
  (identificador de jugador), nombres de invocador de otros jugadores ni el contenido de `data/crudo/`.
  De los demás jugadores solo se exporta el campeón del rival de posición.
- **Red:** las pruebas no usan red. La API de Riot solo se llama desde `ingest.py` a través de `RiotClient`.
- **Dependencias:** no agregues paquetes de Python ni de JavaScript sin aprobación.
  La página no usa framework ni paso de compilación.
- **Conocimiento del juego:** no inventes reglas, consejos ni datos de League of Legends
  (matchups, tiempos de objetivos, builds). Ese contenido lo define el supervisor.
- **Alcance:** no refactorices código que la tarea no menciona. No borres archivos existentes
  salvo que la tarea lo pida.
- **Base de datos:** no cambies el esquema de `db.py` salvo que la tarea lo pida.
  La base `data/prepartida.duckdb` contiene datos reales: ábrela en modo solo lectura
  fuera de `ingest.py`.

## Comandos

```bash
source .venv/bin/activate          # entorno de Python
pip install -e ".[dev]"            # tras cambiar pyproject.toml
pytest                             # pruebas de Python (deben pasar todas)
node --test docs/js/calc.test.js   # pruebas de JavaScript (desde T05)
prepartida exportar                # genera docs/data/*.json (desde T03)
python -m http.server 8000 -d docs # ver la página en http://localhost:8000
```

## Convenciones de código

**Python**
- Python 3.11 o superior. `from __future__ import annotations` en cada módulo.
- Nombres de funciones, variables, tablas y columnas en español, sin tildes ni ñ en identificadores.
- Tipos en las firmas. Docstring de una línea en funciones públicas.
- Cada módulo nuevo tiene pruebas en `tests/`. Usa la API simulada de `tests/conftest.py`.

**JavaScript**
- Módulos ES nativos (`<script type="module">`). Sin TypeScript, sin empaquetador, sin npm.
- La lógica de cálculo va en funciones puras en `docs/js/calc.js`, con pruebas en `docs/js/calc.test.js`
  usando `node:test` y `node:assert`.
- Las vistas no calculan: reciben datos ya calculados y solo dibujan.
- Nombres en español, igual que en Python.

**Interfaz**
- Todo el texto visible en español.
- Toda tasa o promedio se muestra con su número de partidas ("48 % · 56 partidas").
- Con menos de 10 partidas, muestra la etiqueta "muestra pequeña".
- El color nunca es la única señal: victoria y derrota llevan también texto o icono.
- Usa solo los colores y tamaños definidos en `docs/css/tokens.css`.
- Toda imagen lleva `alt`. Si una imagen no carga, se muestra el nombre en texto.

## Mapa del repositorio

```
src/prepartida/
  config.py       lee .env
  perfil.py       lee perfil.toml (pool, roles, metas)
  riot_client.py  cliente de la API de Riot con limitador de tasa
  ingest.py       descarga perfil e historial
  parse.py        respuestas de la API -> filas
  db.py           esquema DuckDB
  ddragon.py      datos estáticos oficiales (campeones, ítems, runas, hechizos)
  metricas.py     métricas por partida y agregados
  estado.py       resumen en texto
  app.py          app Streamlit provisional (se retira en T13)
  cli.py          comandos
tests/            pruebas de Python
docs/             página estática publicada (se crea en T04)
data/             base local y respuestas crudas (no se versiona)
reglas/           reglas del juego por parche (sin verificar; no usar todavía)
perfil.toml       pool, roles y metas del jugador
PLAN.md           tareas
BITACORA.md       registro de trabajo
```
