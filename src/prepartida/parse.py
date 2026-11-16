"""Convierte las respuestas de match-v5 en filas para la base local."""

from __future__ import annotations

import json
from datetime import datetime, timezone

LADOS = {100: "azul", 200: "rojo"}


def _ts(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)


def parche_de(version_juego: str) -> str:
    """'16.22.701.1234' -> '16.22'."""
    partes = version_juego.split(".")
    return ".".join(partes[:2]) if len(partes) >= 2 else version_juego


def fila_partida(partida: dict) -> tuple:
    info = partida["info"]
    gana_azul = next((t.get("win") for t in info.get("teams", []) if t.get("teamId") == 100), None)
    version = info.get("gameVersion", "")
    return (
        partida["metadata"]["matchId"],
        version,
        parche_de(version),
        info.get("queueId"),
        _ts(info.get("gameCreation")),
        info.get("gameDuration"),
        gana_azul,
    )


def filas_participantes(partida: dict) -> list[tuple]:
    match_id = partida["metadata"]["matchId"]
    filas = []
    for p in partida["info"]["participants"]:
        estilos = (p.get("perks") or {}).get("styles") or []
        primario = estilos[0] if len(estilos) > 0 else {}
        secundario = estilos[1] if len(estilos) > 1 else {}
        selecciones = primario.get("selections") or [{}]
        filas.append(
            (
                match_id,
                p.get("participantId"),
                p.get("puuid"),
                LADOS.get(p.get("teamId"), "?"),
                p.get("championId"),
                p.get("championName"),
                p.get("teamPosition") or p.get("individualPosition"),
                p.get("win"),
                p.get("kills"),
                p.get("deaths"),
                p.get("assists"),
                (p.get("totalMinionsKilled") or 0) + (p.get("neutralMinionsKilled") or 0),
                p.get("goldEarned"),
                p.get("totalDamageDealtToChampions"),
                p.get("visionScore"),
                *[p.get(f"item{i}") for i in range(7)],
                p.get("summoner1Id"),
                p.get("summoner2Id"),
                selecciones[0].get("perk"),
                primario.get("style"),
                secundario.get("style"),
            )
        )
    return filas


def filas_cuadros(linea: dict) -> list[tuple]:
    match_id = linea["metadata"]["matchId"]
    filas = []
    for minuto, cuadro in enumerate(linea["info"].get("frames", [])):
        for pid, pf in (cuadro.get("participantFrames") or {}).items():
            pos = pf.get("position") or {}
            filas.append(
                (
                    match_id,
                    int(pid),
                    minuto,
                    pf.get("totalGold"),
                    pf.get("xp"),
                    pf.get("minionsKilled"),
                    pf.get("jungleMinionsKilled"),
                    pos.get("x"),
                    pos.get("y"),
                )
            )
    return filas


def filas_eventos(linea: dict) -> list[tuple]:
    match_id = linea["metadata"]["matchId"]
    filas = []
    for cuadro in linea["info"].get("frames", []):
        for ev in cuadro.get("events", []):
            pid = ev.get("participantId") or ev.get("killerId") or ev.get("creatorId")
            filas.append(
                (
                    match_id,
                    ev.get("timestamp"),
                    ev.get("type"),
                    pid if pid else None,
                    json.dumps(ev, ensure_ascii=False),
                )
            )
    return filas
