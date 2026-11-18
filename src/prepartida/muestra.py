"""Muestra de partidas de otro rango para comparación."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import duckdb

from prepartida import db, ingest
from prepartida.riot_client import NoEncontrado, RateLimiter, RiotClient, RiotError

COLA_SOLO_DUO = 420
DIVISIONES = ("I", "II", "III", "IV")
LIMITE_DIAS = 30
PAGINAS_MAX_DEFAULT = 10


def crear_tabla_muestra(con: duckdb.DuckDBPyConnection) -> None:
    """Crea la tabla muestra_partidas si no existe."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS muestra_partidas (
            match_id VARCHAR PRIMARY KEY,
            tier_muestra VARCHAR,
            fecha_muestra TIMESTAMP
        )
    """
    )


def _partidas_ya_guardadas(con: duckdb.DuckDBPyConnection) -> set[str]:
    """Devuelve el conjunto de match_id ya registrados en la muestra."""
    filas = con.execute("SELECT match_id FROM muestra_partidas").fetchall()
    return {fila[0] for fila in filas}


def _es_reciente(momento: datetime | None, limite_dias: int = LIMITE_DIAS) -> bool:
    """Devuelve True si el momento está dentro de los últimos límite_dias días."""
    if momento is None:
        return False
    umbral = datetime.now(timezone.utc) - timedelta(days=limite_dias)
    return momento >= umbral


def _recolectar_participantes(
    cliente: RiotClient,
    tier: str,
    division: str,
    cupo: int,
    max_paginas: int,
    rng: random.Random,
) -> list[str]:
    """Devuelve PUUIDs de jugadores de una división, de páginas elegidas al azar.

    Pide páginas entre 1 y max_paginas en orden aleatorio hasta reunir
    cupo * 3 jugadores. Una página vacía (la división tiene menos páginas) o
    con error se salta, para no gastar llamadas de más.
    """
    paginas = list(range(1, max_paginas + 1))
    rng.shuffle(paginas)
    meta = cupo * 3
    jugadores: list[str] = []
    for pagina in paginas:
        if len(jugadores) >= meta:
            break
        try:
            lote = cliente.entradas_de_liga(tier, division, pagina)
        except RiotError:
            continue
        for entrada in lote:
            if "puuid" in entrada:
                jugadores.append(entrada["puuid"])
    rng.shuffle(jugadores)
    return jugadores[:meta]


def _tomar_de_jugador(
    con: duckdb.DuckDBPyConnection,
    cliente: RiotClient,
    puuid: str,
    tier: str,
    maximo: int,
    inicio_tiempo: int,
    ya: set[str],
) -> int:
    """Guarda hasta `maximo` partidas recientes de un jugador. Devuelve cuántas."""
    try:
        ids = cliente.ids_de_partidas(puuid, queue=COLA_SOLO_DUO, start_time=inicio_tiempo)
    except RiotError:
        return 0  # jugador con error: se salta

    tomadas = 0
    for match_id in ids:
        if tomadas >= maximo:
            break
        if match_id in ya:
            continue
        try:
            partida = cliente.partida(match_id)
            linea = cliente.linea_de_tiempo(match_id)  # sin timeline no sirve
        except RiotError:
            continue
        momento = datetime.fromtimestamp(
            partida["info"]["gameCreation"] / 1000, tz=timezone.utc
        )
        if not _es_reciente(momento):
            continue
        ingest.guardar_partida(con, partida, linea)
        con.execute(
            "INSERT OR REPLACE INTO muestra_partidas VALUES (?, ?, ?)",
            [match_id, tier, momento],
        )
        ya.add(match_id)
        tomadas += 1
    return tomadas


def run(
    con: duckdb.DuckDBPyConnection,
    cliente: RiotClient,
    tier: str,
    partidas_objetivo: int,
    por_jugador: int,
    semilla: int | None,
    max_paginas: int = PAGINAS_MAX_DEFAULT,
    aviso: Callable[[str], None] = print,
) -> dict:
    """Descarga una muestra de partidas del tier dado, repartida por divisiones.

    Cada división tiene un cupo de ceil(objetivo / 4); lo que una no logra
    llenar pasa a la siguiente. Siempre termina con una línea de resumen.
    """
    crear_tabla_muestra(con)
    rng = random.Random(semilla)
    inicio_tiempo = int(
        (datetime.now(timezone.utc) - timedelta(days=LIMITE_DIAS)).timestamp()
    )
    cupo_base = math.ceil(partidas_objetivo / len(DIVISIONES))
    por_division: dict[str, int] = {d: 0 for d in DIVISIONES}
    total = 0
    sobrante = 0
    ya = _partidas_ya_guardadas(con)

    for division in DIVISIONES:
        cupo = min(cupo_base + sobrante, partidas_objetivo - total)
        if cupo <= 0:
            break
        jugadores = _recolectar_participantes(
            cliente, tier, division, cupo, max_paginas, rng
        )
        for puuid in jugadores:
            if por_division[division] >= cupo:
                break
            tomadas = _tomar_de_jugador(
                con,
                cliente,
                puuid,
                tier,
                min(por_jugador, cupo - por_division[division]),
                inicio_tiempo,
                ya,
            )
            por_division[division] += tomadas
            total += tomadas
            if tomadas and total // 25 != (total - tomadas) // 25:
                aviso(f"{tier}: {total} de {partidas_objetivo} partidas")
        sobrante = cupo - por_division[division]

    partes = ", ".join(f"{d}: {n}" for d, n in por_division.items())
    aviso(f"{tier}: {total} de {partidas_objetivo} partidas ({partes})")
    return {"partidas": total, "por_division": por_division}
