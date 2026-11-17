# prepartida

Herramienta personal de preparación pre-partida para SoloQ de League of Legends.
Documento de diseño: `claude/herramienta-prepartida-lol.md` en el proyecto de Claude.

## Estado: fase 1b (página estática en GitHub Pages)

Hecho:
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
prepartida app                  # abre la app web local en el navegador
```

Para ver la página estática en local:

```bash
python -m http.server 8000 -d docs
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
  app.py           app web local (Streamlit)
  cli.py           comandos
reglas/            reglas del juego por parche (por verificar)
data/              base local y respuestas crudas (no se versiona)
docs/              página estática publicada en GitHub Pages
```

