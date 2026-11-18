from __future__ import annotations

import json

import httpx

from prepartida import cli, db, ingest, referencias
from prepartida.riot_client import RateLimiter, RiotClient
from test_cli import _base, _estaticos_falsos

ROLES = ("MIDDLE", "BOTTOM")
METRICAS = ("cs_10", "dif_oro_10", "dif_oro_15", "muertes_14")


def _muestra(api, ruta, tier="GOLD"):
    """Base de muestra con las 3 partidas simuladas, marcadas con un tier."""
    con = db.conectar(ruta)
    cliente = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(limites=((10**9, 1.0),), sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    for mid in api.ids:
        ingest.guardar_partida(con, cliente.partida(mid), cliente.linea_de_tiempo(mid))
    con.execute(
        "CREATE TABLE muestra_partidas (match_id VARCHAR PRIMARY KEY, tier_muestra VARCHAR, fecha_muestra TIMESTAMP)"
    )
    for mid in api.ids:
        con.execute("INSERT INTO muestra_partidas VALUES (?, ?, now())", [mid, tier])
    return con


def test_contrato_de_referencias(api, tmp_path):
    con = _muestra(api, tmp_path / "muestra.duckdb")
    ref = referencias.construir(con)
    assert ref["generado"].endswith("Z")
    assert ref["parches"] == ["16.22"]
    oro = ref["rangos"]["GOLD"]
    assert oro["partidas"] == 3
    for rol in ROLES:
        r = oro[rol]
        assert r["observaciones"] == 6  # 3 partidas x 2 equipos
        assert r["muestra_pequena"] is True  # menos de 100
        for m in METRICAS:
            assert set(r[m]) == {"p25", "p50", "p75"}
            assert r[m]["p25"] <= r[m]["p50"] <= r[m]["p75"]
        assert len(r["curva_cs"]) == 21
        assert r["curva_cs"][10] == r["cs_10"]["p50"] == 70
        assert [b["muertes"] for b in r["por_muertes_14"]] == ["0", "1", "2+"]
        assert sum(b["partidas"] for b in r["por_muertes_14"]) == 6
    # Simetría: cada línea aporta las dos caras.
    assert oro["MIDDLE"]["dif_oro_10"]["p25"] == -oro["MIDDLE"]["dif_oro_10"]["p75"]


def test_tasa_por_muertes(api, tmp_path):
    con = _muestra(api, tmp_path / "muestra.duckdb")
    ref = referencias.construir(con)
    cubos = {b["muertes"]: b for b in ref["rangos"]["GOLD"]["MIDDLE"]["por_muertes_14"]}
    # En la API simulada el 3 mata al 8 al minuto 5: el 8 (MIDDLE rojo) tiene 1 muerte.
    assert cubos["1"]["partidas"] == 3
    assert cubos["0"]["partidas"] == 3
    assert cubos["2+"]["partidas"] == 0 and cubos["2+"]["tasa"] is None
    # LA1_2 la pierde el azul: el rojo gana 1 de 3 con 1 muerte.
    assert cubos["1"]["tasa"] == round(100 * 1 / 3, 1)


def test_sin_puuids_ni_match_ids(api, tmp_path):
    con = _muestra(api, tmp_path / "muestra.duckdb")
    texto = json.dumps(referencias.construir(con))
    for mid in api.ids:
        assert mid not in texto
    assert "puuid" not in texto
    for (puuid,) in con.execute("SELECT DISTINCT puuid FROM participantes").fetchall():
        assert puuid not in texto


def test_varios_rangos(api, tmp_path):
    con = _muestra(api, tmp_path / "muestra.duckdb")
    con.execute("UPDATE muestra_partidas SET tier_muestra = 'DIAMOND' WHERE match_id = 'LA1_3'")
    ref = referencias.construir(con)
    assert ref["rangos"]["GOLD"]["partidas"] == 2
    assert ref["rangos"]["DIAMOND"]["partidas"] == 1


def test_exportar_escribe_referencias_si_hay_muestra(api, tmp_path, monkeypatch):
    datos = tmp_path / "data"
    datos.mkdir()
    _base(api, datos)
    _estaticos_falsos(datos / "estaticos")
    _muestra(api, datos / "muestra.duckdb").close()
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(datos))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["exportar"]) == 0
    ref = json.loads((tmp_path / "docs" / "data" / "referencias.json").read_text(encoding="utf-8"))
    assert "GOLD" in ref["rangos"]


def test_exportar_sin_muestra_no_crea_referencias(api, tmp_path, monkeypatch):
    datos = tmp_path / "data"
    datos.mkdir()
    _base(api, datos)
    _estaticos_falsos(datos / "estaticos")
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(datos))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["exportar"]) == 0
    assert not (tmp_path / "docs" / "data" / "referencias.json").exists()
