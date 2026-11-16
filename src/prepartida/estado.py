"""Resumen del perfil: rango y rendimiento por campeón y posición."""

from __future__ import annotations

import duckdb

# Contracción hacia el 50 %: equivale a sumar 10 partidas ficticias (5 ganadas, 5 perdidas).
# Con pocas partidas, la tasa ajustada se queda cerca del 50 %.
PRIOR_PARTIDAS = 10


def rango_actual(con: duckdb.DuckDBPyConnection, puuid: str) -> tuple | None:
    return con.execute(
        "SELECT tier, division, lp, victorias, derrotas FROM rango_historial "
        "WHERE puuid = ? AND cola = 'RANKED_SOLO_5x5' ORDER BY tomado DESC LIMIT 1",
        [puuid],
    ).fetchone()


def por_campeon(con: duckdb.DuckDBPyConnection, puuid: str) -> list[tuple]:
    """Filas: campeón, posición, partidas, victorias, tasa cruda, tasa ajustada,
    KDA, CS por minuto y diferencia de oro al minuto 15 frente al rival de posición."""
    return con.execute(
        f"""
        WITH mias AS (
            SELECT p.*, m.duracion_s
            FROM participantes p JOIN partidas m USING (match_id)
            WHERE p.puuid = ?
        ),
        oro15 AS (
            SELECT yo.match_id,
                   c_yo.oro_total - c_rival.oro_total AS dif_oro_15
            FROM mias yo
            JOIN participantes rival
              ON rival.match_id = yo.match_id
             AND rival.posicion = yo.posicion
             AND rival.lado <> yo.lado
            JOIN cuadros c_yo
              ON c_yo.match_id = yo.match_id
             AND c_yo.participant_id = yo.participant_id AND c_yo.minuto = 15
            JOIN cuadros c_rival
              ON c_rival.match_id = rival.match_id
             AND c_rival.participant_id = rival.participant_id AND c_rival.minuto = 15
            WHERE yo.posicion IS NOT NULL AND yo.posicion <> ''
        )
        SELECT mias.campeon,
               mias.posicion,
               count(*) AS partidas,
               sum(victoria::INT) AS victorias,
               round(100.0 * sum(victoria::INT) / count(*), 1) AS tasa,
               round(100.0 * (sum(victoria::INT) + {PRIOR_PARTIDAS} / 2.0)
                     / (count(*) + {PRIOR_PARTIDAS}), 1) AS tasa_ajustada,
               round((sum(asesinatos) + sum(asistencias)) / greatest(sum(muertes), 1), 2) AS kda,
               round(avg(cs / (duracion_s / 60.0)), 1) AS cs_min,
               round(avg(oro15.dif_oro_15)) AS dif_oro_15
        FROM mias LEFT JOIN oro15 USING (match_id)
        GROUP BY mias.campeon, mias.posicion
        ORDER BY partidas DESC
        """,
        [puuid],
    ).fetchall()


def texto(con: duckdb.DuckDBPyConnection) -> str:
    jugador = con.execute(
        "SELECT puuid, game_name, tag_line FROM jugador ORDER BY actualizado DESC LIMIT 1"
    ).fetchone()
    if jugador is None:
        return "Aún no hay jugador en la base. Ejecuta primero: prepartida ingesta"
    puuid, nombre, tag = jugador
    lineas = [f"{nombre} #{tag}"]
    rango = rango_actual(con, puuid)
    if rango:
        tier, division, lp, v, d = rango
        lineas.append(f"Solo/Dúo: {tier} {division}, {lp} LP ({v} victorias, {d} derrotas)")
    total = con.execute(
        "SELECT count(*) FROM participantes WHERE puuid = ?", [puuid]
    ).fetchone()[0]
    lineas.append(f"Partidas en la base: {total}")
    filas = por_campeon(con, puuid)
    if filas:
        lineas.append("")
        lineas.append(
            f"{'Campeón':<14}{'Posición':<10}{'Part.':>6}{'Vict.':>6}{'Tasa':>7}"
            f"{'Ajust.':>8}{'KDA':>6}{'CS/min':>8}{'Oro@15':>8}"
        )
        for campeon, pos, n, v, tasa, ajustada, kda, cs_min, dif in filas:
            dif_txt = f"{int(dif):+d}" if dif is not None else "-"
            lineas.append(
                f"{campeon or '?':<14}{pos or '-':<10}{n:>6}{v:>6}{tasa:>6}%"
                f"{ajustada:>7}%{kda:>6}{cs_min:>8}{dif_txt:>8}"
            )
        lineas.append("")
        lineas.append(
            "Ajust. = tasa de victorias contraída hacia el 50 % "
            f"(prior de {PRIOR_PARTIDAS} partidas). Oro@15 = diferencia media de oro "
            "al minuto 15 frente al rival de tu posición."
        )
    return "\n".join(lineas)
