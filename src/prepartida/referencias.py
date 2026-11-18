"""Referencias por rango (contrato, sección 3.8 de PLAN.md).

Lee la base de muestra (`data/muestra.duckdb`) y publica solo agregados:
percentiles, tasas por muertes tempranas y la curva mediana de CS. Nunca
exporta PUUIDs ni match_id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import duckdb
import pandas as pd

from prepartida import metricas

ROLES = ("MIDDLE", "BOTTOM")
MUESTRA_MINIMA = 100
MINUTO_FINAL_CURVA = 20
# métrica -> decimales al redondear los percentiles
DECIMALES = {"cs_10": 1, "dif_oro_10": 0, "dif_oro_15": 0, "muertes_14": 1}

SQL_CURVA = """
SELECT ms.tier_muestra, p.posicion, c.minuto,
       median(c.cs + c.cs_jungla) AS cs
FROM participantes p
JOIN partidas m USING (match_id)
JOIN muestra_partidas ms USING (match_id)
JOIN cuadros c ON c.match_id = p.match_id AND c.participant_id = p.participant_id
WHERE list_contains(?, p.posicion) AND m.duracion_s >= ? AND c.minuto <= ?
GROUP BY 1, 2, 3
"""


def _redondear(valor: float, decimales: int) -> int | float | None:
    if valor is None or pd.isna(valor):
        return None
    return int(round(valor)) if decimales == 0 else round(float(valor), decimales)


def _percentiles(serie: pd.Series, decimales: int) -> dict[str, Any]:
    s = serie.dropna()
    if s.empty:
        return {"p25": None, "p50": None, "p75": None}
    return {
        f"p{int(q * 100)}": _redondear(s.quantile(q), decimales) for q in (0.25, 0.5, 0.75)
    }


def _por_muertes(df: pd.DataFrame) -> list[dict[str, Any]]:
    d = df[df["muertes_14"].notna()]
    cubos = d["muertes_14"].clip(upper=2).map({0: "0", 1: "1", 2: "2+"})
    salida = []
    for etiqueta in ("0", "1", "2+"):
        g = d[cubos == etiqueta]
        tasa = round(100.0 * float(g["victoria"].sum()) / len(g), 1) if len(g) else None
        salida.append({"muertes": etiqueta, "partidas": int(len(g)), "tasa": tasa})
    return salida


def _clave_parche(parche: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in parche.split("."))
    except ValueError:
        return (0,)


def construir(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Arma el diccionario de `referencias.json` a partir de la base de muestra."""
    df = metricas.metricas_por_rol(con, ROLES)
    df = df[df["tier_muestra"].notna()]
    curvas = con.execute(
        SQL_CURVA, [list(ROLES), metricas.DURACION_MINIMA_S, MINUTO_FINAL_CURVA]
    ).df()

    rangos: dict[str, Any] = {}
    for tier, dt in df.groupby("tier_muestra"):
        bloque: dict[str, Any] = {"partidas": int(dt["match_id"].nunique())}
        for rol in ROLES:
            dr = dt[dt["posicion"] == rol]
            cr = curvas[(curvas["tier_muestra"] == tier) & (curvas["posicion"] == rol)]
            por_minuto = dict(zip(cr["minuto"], cr["cs"]))
            r: dict[str, Any] = {"observaciones": int(len(dr))}
            if len(dr) < MUESTRA_MINIMA:
                r["muestra_pequena"] = True
            for metrica, dec in DECIMALES.items():
                r[metrica] = _percentiles(dr[metrica], dec)
            r["por_muertes_14"] = _por_muertes(dr)
            r["curva_cs"] = [
                _redondear(por_minuto.get(m), 1) for m in range(MINUTO_FINAL_CURVA + 1)
            ]
            bloque[rol] = r
        rangos[str(tier)] = bloque

    return {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parches": sorted({str(p) for p in df["parche"].dropna()}, key=_clave_parche),
        "rangos": rangos,
    }
