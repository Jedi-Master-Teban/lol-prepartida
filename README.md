# prepartida

Herramienta personal de preparación pre-partida para SoloQ de League of Legends.
Documento de diseño: `claude/herramienta-prepartida-lol.md` en el proyecto de Claude.

**Página publicada:** https://jedi-master-teban.github.io/lol-prepartida/

## Estado: fase 2 (referencias por rango) casi terminada

Fase 2, hecha (R01 a R05):
- Muestra de partidas de otro rango (`prepartida muestra --tier GOLD`), repartida entre las cuatro
  divisiones, en una base aparte (`data/muestra.duckdb`).
- `referencias.json`: percentiles, tasas por muertes tempranas y curva mediana de CS por rango y rol,
  sin identificadores de otros jugadores.
- En la página: reglas frente a la mediana de Oro en Inicio, bloque "Tu brecha más grande frente a
  Oro" y curva de Oro en Línea.

Pendiente de la fase 2: R06 (actualización semanal de las referencias en GitHub Actions).

Fase 1b, hecha (página estática en GitHub Pages):
- Cliente de la API (interfaz de programación) de Riot con limitador de tasa
  (20 peticiones por segundo y 100 cada 2 minutos) y reintentos.
- Ingesta de perfil (rango, maestrías) e historial de partidas con línea de tiempo.
- Base local en DuckDB y copia cruda comprimida de cada respuesta.
- Descarga de datos estáticos oficiales (Data Dragon): campeones, ítems, runas, hechizos.
- Resumen `estado`: rendimiento por campeón y posición.
- Métricas de línea por partida: CS al minuto 10, diferencia de oro a los 10 y 15 minutos
  frente al rival de posición y muertes antes del minuto 14.
- Página estática en `docs/` con métricas, gráficas y vistas de pool, línea, muertes y partidas.
- Comandos `exportar` y `publicar` para generar y subir los datos.

Pendiente de la fase 0:
- Verificar `reglas/objetivos.toml` contra las notas de parche oficiales.
- Decidir cómo tomar cifras de páginas de terceros (Lolalytics, U.GG, OP.GG).
- Verificar la API local del juego en partida para el panel de ítems (opcional).

## Puesta en marcha

Requiere Python 3.11 o superior.

```bash
cd lol-prepartida
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # y pega tu clave en RIOT_API_KEY
```

La clave se obtiene en https://developer.riotgames.com. La de desarrollo sirve para
empezar pero expira cada 24 horas; la personal no expira y se solicita en el mismo portal.

## Uso

```bash
prepartida init                 # crea data/prepartida.duckdb
prepartida estaticos            # campeones, ítems, runas y hechizos del parche actual
prepartida ingesta --max 200    # tu perfil y tus últimas partidas de Solo/Dúo
prepartida estado               # rango y rendimiento por campeón
prepartida exportar             # genera docs/data/*.json para la página estática
```

Para ver la página estática en local:

```bash
python3 -m http.server 8000 -d docs
```

y abrir http://localhost:8000 en el navegador.

El pool, los roles y las metas se editan en `perfil.toml`.

`ingesta` solo descarga las partidas que falten, así que se puede repetir después de cada sesión.
Con la clave personal, 200 partidas con línea de tiempo tardan unos 8 minutos por el límite
de 100 peticiones cada 2 minutos.

## Publicación en GitHub Pages

La página se publica desde la carpeta `docs/` en GitHub Pages. Los pasos que hace el usuario:

1. Crear un repositorio público en GitHub y agregarlo como remoto `origin`.
2. `git push -u origin main`.
3. En el repositorio: Settings → Pages → Source "Deploy from a branch" → rama `main`, carpeta `/docs`.

Antes del primer push, comprueba que `git ls-files` no incluye `.env` ni nada de `data/`,
y que `git grep -nE "RGAPI-[0-9a-f]{8}-"` no devuelve nada.

## Actualización automática con GitHub Actions

La página se actualiza automáticamente cada 3 horas mediante un workflow de GitHub Actions
(`.github/workflows/actualizar.yml`). El workflow:

- Se ejecuta cada 3 horas (`schedule`) y también se puede lanzar manualmente desde la
  pestaña **Actions** del repositorio (`workflow_dispatch`).
- Descarga los datos estáticos de Data Dragon, hace ingesta de tus últimas 200 partidas
  y exporta los JSON a `docs/data/`. Si hubo cambios, hace commit y push automáticamente.
- Usa el secreto `RIOT_API_KEY` (tu clave personal de Riot) y las variables del repositorio
  `RIOT_GAME_NAME`, `RIOT_TAG_LINE`, `RIOT_PLATFORM` y `RIOT_REGION`.
- La clave nunca se imprime en los registros.

Para configurarlo:

1. En GitHub: Settings → Secrets and variables → Actions.
2. Añade el secreto `RIOT_API_KEY` con tu clave personal de Riot.
3. Añade las variables `RIOT_GAME_NAME`, `RIOT_TAG_LINE`, `RIOT_PLATFORM` y
   `RIOT_REGION` con los valores de tu cuenta.

Puedes ver las ejecuciones en la pestaña **Actions** del repositorio y lanzar una
manualmente con el botón "Run workflow".

## Pruebas

```bash
pytest
```

Las pruebas usan una API simulada y no necesitan clave ni red.

## Estructura

```
src/prepartida/
  config.py        configuración (.env)
  riot_client.py   cliente y limitador de tasa
  ingest.py        ingesta de perfil e historial
  parse.py         respuestas de match-v5 -> filas
  db.py            esquema DuckDB
  ddragon.py       datos estáticos
  estado.py        resumen por campeón
  metricas.py      métricas de línea y agregados
  perfil.py        lectura de perfil.toml
  cli.py           comandos
reglas/            reglas del juego por parche (por verificar)
data/              base local y respuestas crudas (no se versiona)
docs/              página estática publicada en GitHub Pages
.github/workflows/
  actualizar.yml   actualización automática cada 3 horas
```

