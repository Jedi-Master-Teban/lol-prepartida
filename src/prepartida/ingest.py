"""Ingesta del perfil y del historial de partidas del jugador."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import duckdb

from prepartida import parse
from prepartida.riot_client import COLA_SOLO_DUO, NoEncontrado, RiotClient


def _guardar_crudo(raw_dir: Path | None, nombre: str, datos: dict) -> None:
    if raw_dir is None:
        return
    raw_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw_dir / f"{nombre}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)


def _insertar(con: duckdb.DuckDBPyConnection, tabla: str, filas: list[tuple]) -> None:
    if not filas:
        return
    marcas = ", ".join("?" for _ in filas[0])
    con.executemany(f"INSERT OR REPLACE INTO {tabla} VALUES ({marcas})", filas)


def guardar_partida(
    con: duckdb.DuckDBPyConnection, partida: dict, linea: dict | None
) -> None:
    match_id = partida["metadata"]["matchId"]
    con.execute("BEGIN")
    try:
        _insertar(con, "partidas", [parse.fila_partida(partida)])
        _insertar(con, "participantes", parse.filas_participantes(partida))
        if linea is not None:
            con.execute("DELETE FROM eventos WHERE match_id = ?", [match_id])
            _insertar(con, "cuadros", parse.filas_cuadros(linea))
            eventos = parse.filas_eventos(linea)
            if eventos:
                con.executemany("INSERT INTO eventos VALUES (?, ?, ?, ?, ?)", eventos)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def _migrar_puuid(
    con: duckdb.DuckDBPyConnection, puuid: str, game_name: str, tag_line: str
) -> None:
    """Pasa los datos de la misma cuenta guardados con otro PUUID al PUUID actual.

    Riot cifra el PUUID según la clave de API: al cambiar de clave (por ejemplo,
    de desarrollo a personal) la misma cuenta llega con otro PUUID. Sin esta
    migración las partidas ya guardadas quedarían huérfanas.
    """
    viejos = [
        fila[0]
        for fila in con.execute(
            "SELECT puuid FROM jugador WHERE lower(game_name) = lower(?) "
            "AND lower(tag_line) = lower(?) AND puuid <> ?",
            [game_name, tag_line, puuid],
        ).fetchall()
    ]
    if not viejos:
        return
    con.execute("BEGIN")
    try:
        for viejo in viejos:
            con.execute("UPDATE participantes SET puuid = ? WHERE puuid = ?", [puuid, viejo])
            con.execute("DELETE FROM rango_historial WHERE puuid = ?", [viejo])
            con.execute("DELETE FROM maestria WHERE puuid = ?", [viejo])
            con.execute("DELETE FROM jugador WHERE puuid = ?", [viejo])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def ingerir_perfil(
    client: RiotClient, con: duckdb.DuckDBPyConnection, game_name: str, tag_line: str
) -> str:
    """Resuelve el Riot ID, guarda rango y maestrías. Devuelve el PUUID."""
    cuenta = client.cuenta_por_riot_id(game_name, tag_line)
    puuid = cuenta["puuid"]
    _migrar_puuid(con, puuid, cuenta.get("gameName", game_name), cuenta.get("tagLine", tag_line))
    con.execute(
        "INSERT OR REPLACE INTO jugador (puuid, game_name, tag_line, plataforma) VALUES (?, ?, ?, ?)",
        [puuid, cuenta.get("gameName", game_name), cuenta.get("tagLine", tag_line), client.platform],
    )
    for liga in client.ligas_por_puuid(puuid):
        con.execute(
            "INSERT INTO rango_historial (puuid, cola, tier, division, lp, victorias, derrotas) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                puuid,
                liga.get("queueType"),
                liga.get("tier"),
                liga.get("rank"),
                liga.get("leaguePoints"),
                liga.get("wins"),
                liga.get("losses"),
            ],
        )
    maestrias = []
    for m in client.maestrias_por_puuid(puuid):
        ultima = m.get("lastPlayTime")
        maestrias.append(
            (
                puuid,
                m.get("championId"),
                m.get("championLevel"),
                m.get("championPoints"),
                datetime.fromtimestamp(ultima / 1000, tz=timezone.utc).replace(tzinfo=None)
                if ultima
                else None,
            )
        )
    _insertar(con, "maestria", maestrias)
    return puuid


def ingerir_historial(
    client: RiotClient,
    con: duckdb.DuckDBPyConnection,
    puuid: str,
    max_partidas: int = 200,
    queue: int | None = COLA_SOLO_DUO,
    raw_dir: Path | None = None,
    aviso: Callable[[str], None] = lambda _msg: None,
) -> dict[str, int]:
    """Descarga las partidas que falten, con su línea de tiempo."""
    ids: list[str] = []
    inicio = 0
    while len(ids) < max_partidas:
        lote = client.ids_de_partidas(
            puuid, queue=queue, start=inicio, count=min(100, max_partidas - len(ids))
        )
        if not lote:
            break
        ids.extend(lote)
        inicio += len(lote)

    ya = {r[0] for r in con.execute("SELECT match_id FROM partidas").fetchall()}
    nuevas = [i for i in ids if i not in ya]
    aviso(f"{len(ids)} partidas en el historial, {len(nuevas)} por descargar")

    guardadas = 0
    sin_linea = 0
    for n, match_id in enumerate(nuevas, 1):
        partida = client.partida(match_id)
        try:
            linea = client.linea_de_tiempo(match_id)
        except NoEncontrado:
            linea = None
            sin_linea += 1
        _guardar_crudo(raw_dir, match_id, partida)
        if linea is not None:
            _guardar_crudo(raw_dir, f"{match_id}_timeline", linea)
        guardar_partida(con, partida, linea)
        guardadas += 1
        if n % 10 == 0 or n == len(nuevas):
            aviso(f"  {n}/{len(nuevas)}")
    return {"encontradas": len(ids), "nuevas": guardadas, "sin_linea_de_tiempo": sin_linea}
