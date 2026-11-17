"""Muestra de partidas de otro rango para comparación."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import duckdb

from prepartida import db, ingest
from prepartida.riot_client import RateLimiter, RiotClient

COLA_SOLO_DUO = 420
DIVISIONES = ("I", "II", "III", "IV")
LIMITE_DIAS = 30


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


def run(
    con: duckdb.DuckDBPyConnection,
    cliente: RiotClient,
    tier: str,
    partidas_objetivo: int,
    por_jugador: int,
    semilla: int | None,
    aviso: Callable[[str], None] = lambda _msg: None,
) -> dict[str, int]:
    """Descarga una muestra de partidas del tier dado.

    Devuelve un diccionario con el conteo de partidas guardadas.
    """
    crear_tabla_muestra(con)
    rng = random.Random(semilla) if semilla is not None else random
    partidas_totales = 0

    for division in DIVISIONES:
        if partidas_totales >= partidas_objetivo:
            break

        # Recolectar puuid de todos los jugadores de la división
        jugadores: list[str] = []
        pagina = 1
        while True:
            lote = cliente.entradas_de_liga(tier, division, pagina)
            if not lote:
                break
            jugadores.extend(e["puuid"] for e in lote)
            pagina += 1

        rng.shuffle(jugadores)

        for puuid in jugadores:
            if partidas_totales >= partidas_objetivo:
                break

            ya = _partidas_ya_guardadas(con)
            ids = cliente.ids_de_partidas(puuid, queue=COLA_SOLO_DUO)
            tomadas_en_esta_partida = 0

            for match_id in ids:
                if (
                    partidas_totales >= partidas_objetivo
                    or tomadas_en_esta_partida >= por_jugador
                ):
                    break
                if match_id in ya:
                    continue

                partida = cliente.partida(match_id)
                inicio = partida["info"]["gameCreation"]
                momento = datetime.fromtimestamp(inicio / 1000, tz=timezone.utc)

                if not _es_reciente(momento):
                    continue

                try:
                    linea = cliente.linea_de_tiempo(match_id)
                except Exception:
                    linea = None

                ingest.guardar_partida(con, partida, linea)
                con.execute(
                    "INSERT OR REPLACE INTO muestra_partidas VALUES (?, ?, ?)",
                    [match_id, tier, momento],
                )

                ya.add(match_id)
                tomadas_en_esta_partida += 1
                partidas_totales += 1

                if partidas_totales % 25 == 0:
                    aviso(f"{tier}: {partidas_totales} de {partidas_objetivo} partidas")

    return {"partidas": partidas_totales}
