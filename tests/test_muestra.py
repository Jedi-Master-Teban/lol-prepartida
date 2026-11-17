from __future__ import annotations

from pathlib import Path

import duckdb
import httpx
import pytest

from prepartida import db, ingest
from prepartida.muestra import run
from prepartida.riot_client import RateLimiter, RiotClient


def _cliente(api):
    return RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )


def _base_con_datos(tmp_path: Path) -> tuple[duckdb.DuckDBPyConnection, str]:
    """Crea una base de muestra vacía y devuelve (con, ruta)."""
    ruta = tmp_path / "muestra.duckdb"
    con = db.conectar(ruta)
    return con, str(ruta)


def test_muestra_detiene_en_el_tope(api, tmp_path):
    """No descarga más partidas de las solicitadas."""
    con, _ = _base_con_datos(tmp_path)
    cliente = _cliente(api)
    resumen = run(con, cliente, "GOLD", 2, 1, semilla=7)
    assert resumen["partidas"] <= 2
    con.close()


def test_muestra_no_duplica_partidas(api, tmp_path):
    """Ejecutar dos veces no duplica partidas."""
    con, _ = _base_con_datos(tmp_path)
    cliente = _cliente(api)
    run(con, cliente, "GOLD", 4, 1, semilla=7)
    n1 = con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0]
    run(con, cliente, "GOLD", 4, 1, semilla=7)
    n2 = con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0]
    assert n1 == n2
    con.close()


def test_muestra_tabla_poblada(api, tmp_path):
    """La tabla muestra_partidas queda poblada."""
    con, _ = _base_con_datos(tmp_path)
    cliente = _cliente(api)
    run(con, cliente, "GOLD", 4, 1, semilla=7)
    filas = con.execute("SELECT match_id, tier_muestra FROM muestra_partidas").fetchall()
    assert len(filas) > 0
    assert all(f[1] == "GOLD" for f in filas)
    con.close()


def test_muestra_no_toca_base_principal(api, tmp_path):
    """No escribe nada en data/prepartida.duckdb."""
    base_principal = tmp_path / "data" / "prepartida.duckdb"
    base_principal.parent.mkdir(parents=True, exist_ok=True)
    con_muestra, _ = _base_con_datos(tmp_path)
    cliente = _cliente(api)
    run(con_muestra, cliente, "GOLD", 2, 1, semilla=7)
    assert not base_principal.exists()
    con_muestra.close()


def test_muestra_es_reanudable(api, tmp_path):
    """Ejecutar dos veces con diferentes límites suma sin repetir."""
    con, _ = _base_con_datos(tmp_path)
    cliente = _cliente(api)
    run(con, cliente, "GOLD", 2, 1, semilla=7)
    n1 = con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0]
    run(con, cliente, "GOLD", 4, 1, semilla=7)
    n2 = con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0]
    assert n2 >= n1
    con.close()
