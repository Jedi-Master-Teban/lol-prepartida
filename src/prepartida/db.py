"""Esquema de la base local en DuckDB."""

from __future__ import annotations

from pathlib import Path

import duckdb

ESQUEMA = """
CREATE TABLE IF NOT EXISTS jugador (
    puuid VARCHAR PRIMARY KEY,
    game_name VARCHAR,
    tag_line VARCHAR,
    plataforma VARCHAR,
    actualizado TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS rango_historial (
    puuid VARCHAR,
    cola VARCHAR,
    tier VARCHAR,
    division VARCHAR,
    lp INTEGER,
    victorias INTEGER,
    derrotas INTEGER,
    tomado TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS maestria (
    puuid VARCHAR,
    champion_id INTEGER,
    nivel INTEGER,
    puntos INTEGER,
    ultima_partida TIMESTAMP,
    PRIMARY KEY (puuid, champion_id)
);

CREATE TABLE IF NOT EXISTS partidas (
    match_id VARCHAR PRIMARY KEY,
    version_juego VARCHAR,
    parche VARCHAR,
    cola INTEGER,
    inicio TIMESTAMP,
    duracion_s INTEGER,
    gana_azul BOOLEAN
);

CREATE TABLE IF NOT EXISTS participantes (
    match_id VARCHAR,
    participant_id INTEGER,
    puuid VARCHAR,
    lado VARCHAR,
    champion_id INTEGER,
    campeon VARCHAR,
    posicion VARCHAR,
    victoria BOOLEAN,
    asesinatos INTEGER,
    muertes INTEGER,
    asistencias INTEGER,
    cs INTEGER,
    oro INTEGER,
    dano_a_campeones INTEGER,
    vision INTEGER,
    item0 INTEGER, item1 INTEGER, item2 INTEGER, item3 INTEGER,
    item4 INTEGER, item5 INTEGER, item6 INTEGER,
    hechizo1 INTEGER,
    hechizo2 INTEGER,
    runa_clave INTEGER,
    arbol_primario INTEGER,
    arbol_secundario INTEGER,
    PRIMARY KEY (match_id, participant_id)
);

CREATE TABLE IF NOT EXISTS cuadros (
    match_id VARCHAR,
    participant_id INTEGER,
    minuto INTEGER,
    oro_total INTEGER,
    xp INTEGER,
    cs INTEGER,
    cs_jungla INTEGER,
    x INTEGER,
    y INTEGER,
    PRIMARY KEY (match_id, participant_id, minuto)
);

CREATE TABLE IF NOT EXISTS eventos (
    match_id VARCHAR,
    ts_ms BIGINT,
    tipo VARCHAR,
    participant_id INTEGER,
    detalle JSON
);

CREATE TABLE IF NOT EXISTS campeones (
    champion_id INTEGER PRIMARY KEY,
    clave VARCHAR,
    nombre VARCHAR,
    etiquetas VARCHAR,
    version VARCHAR
);

CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY,
    nombre VARCHAR,
    oro_total INTEGER,
    etiquetas VARCHAR,
    version VARCHAR
);
"""


def conectar(ruta: Path | str = ":memory:") -> duckdb.DuckDBPyConnection:
    if ruta != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ruta))
    con.execute(ESQUEMA)
    return con
