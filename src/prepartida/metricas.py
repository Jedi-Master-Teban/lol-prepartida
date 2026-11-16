"""Métricas por partida del jugador y sus agregados.

Todas las tasas se muestran con su número de partidas: con muestras pequeñas
una tasa sola engaña. La tasa ajustada se contrae hacia el 50 %.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd

from prepartida.perfil import Perfil

PRIOR_PARTIDAS = 10
MUESTRA_MINIMA = 10

SQL_PARTIDAS = """
WITH yo AS (
    SELECT p.*, m.duracion_s, m.inicio, m.parche
    FROM participantes p JOIN partidas m USING (match_id)
    WHERE p.puuid = ?
),
muertes AS (
    SELECT match_id,
           CAST(json_extract(detalle, '$.victimId') AS INTEGER) AS pid,
           count(*) FILTER (WHERE ts_ms < 14 * 60000) AS muertes_14,
           min(ts_ms) / 60000.0 AS primera_muerte_min
    FROM eventos WHERE tipo = 'CHAMPION_KILL'
    GROUP BY 1, 2
)
SELECT yo.match_id, yo.inicio, yo.parche, yo.campeon, yo.posicion, yo.lado, yo.victoria,
       yo.asesinatos, yo.muertes, yo.asistencias,
       yo.duracion_s / 60.0 AS duracion_min,
       yo.cs / (yo.duracion_s / 60.0) AS cs_min,
       r.campeon AS rival,
       c10.cs + c10.cs_jungla AS cs_10,
       c10.oro_total - r10.oro_total AS dif_oro_10,
       c15.oro_total - r15.oro_total AS dif_oro_15,
       coalesce(mu.muertes_14, 0) AS muertes_14,
       mu.primera_muerte_min
FROM yo
LEFT JOIN participantes r
       ON r.match_id = yo.match_id AND r.posicion = yo.posicion
      AND r.lado <> yo.lado AND yo.posicion <> ''
LEFT JOIN cuadros c10 ON c10.match_id = yo.match_id AND c10.participant_id = yo.participant_id AND c10.minuto = 10
LEFT JOIN cuadros c15 ON c15.match_id = yo.match_id AND c15.participant_id = yo.participant_id AND c15.minuto = 15
LEFT JOIN cuadros r10 ON r10.match_id = r.match_id AND r10.participant_id = r.participant_id AND r10.minuto = 10
LEFT JOIN cuadros r15 ON r15.match_id = r.match_id AND r15.participant_id = r.participant_id AND r15.minuto = 15
LEFT JOIN muertes mu ON mu.match_id = yo.match_id AND mu.pid = yo.participant_id
ORDER BY yo.inicio
"""


def tasa_ajustada(victorias: float, partidas: float, prior: int = PRIOR_PARTIDAS) -> float:
    """Tasa de victorias (en %) contraída hacia el 50 % con `prior` partidas ficticias."""
    return 100.0 * (victorias + prior / 2.0) / (partidas + prior)


def partidas_del_jugador(
    con: duckdb.DuckDBPyConnection, puuid: str, perfil: Perfil
) -> pd.DataFrame:
    """Una fila por partida, con métricas de línea, pertenencia al pool y orden en la sesión."""
    df = con.execute(SQL_PARTIDAS, [puuid]).df().drop_duplicates("match_id")
    df["victoria"] = df["victoria"].astype(bool)
    df["en_pool"] = df["campeon"].isin(perfil.pool)
    df["dia_sesion"] = (df["inicio"] - pd.Timedelta(hours=perfil.desfase_horas)).dt.date
    df["n_del_dia"] = df.groupby("dia_sesion").cumcount() + 1
    return df.reset_index(drop=True)


def agrupar(df: pd.DataFrame, etiquetas: pd.Series | list[str]) -> pd.DataFrame:
    """Partidas, victorias, tasas y métricas de línea por grupo."""
    columnas = ["partidas", "victorias", "tasa", "tasa_ajustada", "cs_10", "dif_oro_15", "muertes_14"]
    if df.empty:
        return pd.DataFrame(columns=columnas)
    g = df.groupby(etiquetas, dropna=False)
    out = pd.DataFrame(
        {
            "partidas": g["victoria"].size(),
            "victorias": g["victoria"].sum().astype(int),
            "cs_10": g["cs_10"].mean().round(1),
            "dif_oro_15": g["dif_oro_15"].mean().round(0),
            "muertes_14": g["muertes_14"].mean().round(2),
        }
    )
    out["tasa"] = (100.0 * out["victorias"] / out["partidas"]).round(1)
    out["tasa_ajustada"] = tasa_ajustada(out["victorias"], out["partidas"]).round(1)
    return out[columnas].sort_values("partidas", ascending=False)


def por_campeon(df: pd.DataFrame) -> pd.DataFrame:
    return agrupar(df, ["campeon", "posicion"]).reset_index()


def pool_vs_fuera(df: pd.DataFrame) -> pd.DataFrame:
    return agrupar(df, df["en_pool"].map({True: "En el pool", False: "Fuera del pool"}))


def por_posicion(df: pd.DataFrame) -> pd.DataFrame:
    return agrupar(df, "posicion")


def por_muertes_tempranas(df: pd.DataFrame) -> pd.DataFrame:
    etiquetas = df["muertes_14"].clip(upper=2).map({0: "0", 1: "1", 2: "2 o más"})
    return agrupar(df, etiquetas).sort_index()


def por_orden_en_sesion(df: pd.DataFrame, limite: int) -> pd.DataFrame:
    etiquetas = (df["n_del_dia"] <= limite).map(
        {True: f"Partidas 1 a {limite} del día", False: f"Partida {limite + 1} en adelante"}
    )
    return agrupar(df, etiquetas).sort_index(ascending=False)


def partidas_de_hoy(df: pd.DataFrame, perfil: Perfil, ahora: datetime | None = None) -> pd.DataFrame:
    ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
    hoy = (ahora - timedelta(hours=perfil.desfase_horas)).date()
    return df[df["dia_sesion"] == hoy]


def resumen(df: pd.DataFrame) -> dict[str, float | int | None]:
    if df.empty:
        return {"partidas": 0}
    con_linea = df["dif_oro_15"].notna()
    return {
        "partidas": int(len(df)),
        "victorias": int(df["victoria"].sum()),
        "cs_10": round(float(df["cs_10"].mean()), 1),
        "dif_oro_15": round(float(df["dif_oro_15"].mean())) if con_linea.any() else None,
        "por_detras_15": int((df.loc[con_linea, "dif_oro_15"] < 0).sum()),
        "con_dato_15": int(con_linea.sum()),
        "muertes_14": round(float(df["muertes_14"].mean()), 2),
    }
