from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from prepartida import db
from prepartida.config import leer_config
from prepartida.muestra import run
from prepartida.riot_client import RateLimiter, RiotClient

AHORA_MS = int(datetime.now(timezone.utc).timestamp() * 1000)
HACE_60_DIAS_MS = int((datetime.now(timezone.utc) - timedelta(days=60)).timestamp() * 1000)
DIVISIONES = ("I", "II", "III", "IV")


def _cliente(api):
    return RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(limites=((10**9, 1.0),), sleep=lambda _s: None),
        sleep=lambda _s: None,
    )


def _preparar(api, tier="GOLD", por_jugador=3, paginas=3):
    """Cada jugador simulado tiene partidas propias y recientes."""
    for d in DIVISIONES:
        for p in range(1, paginas + 1):
            for k in (1, 2):
                puuid = f"puuid-{tier}-{d}-{p}-{k}"
                ids = [f"M-{d}-{p}-{k}-{n}" for n in range(por_jugador)]
                api.ids_por_puuid[puuid] = ids
                for m in ids:
                    api.creacion[m] = AHORA_MS


def _con(tmp_path):
    return db.conectar(tmp_path / "muestra.duckdb")


def test_el_cupo_se_reparte_entre_las_cuatro_divisiones(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    resumen = run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=lambda _m: None)
    assert resumen["partidas"] == 8
    assert resumen["por_division"] == {"I": 2, "II": 2, "III": 2, "IV": 2}


def test_no_se_leen_todas_las_paginas_de_la_division(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    run(con, _cliente(api), "GOLD", 8, 2, semilla=1, max_paginas=3, aviso=lambda _m: None)
    paginas = [c for c in api.consultas if "RANKED_SOLO_5x5" in c]
    # cupo 2 -> meta de 6 jugadores, pero la API simulada da 2 por página (máx. 3 páginas)
    assert len(paginas) <= 4 * 3


def test_start_time_viaja_en_la_consulta_de_ids(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    run(con, _cliente(api), "GOLD", 4, 1, semilla=1, aviso=lambda _m: None)
    ids = [c for c in api.consultas if c.split("?")[0].endswith("/ids")]
    assert ids and all("startTime=" in c for c in ids)
    inicio = int(ids[0].split("startTime=")[1].split("&")[0])
    esperado = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    assert abs(inicio - esperado) < 120


def test_partida_sin_timeline_no_se_guarda_ni_se_cuenta(api, tmp_path):
    _preparar(api)
    api.sin_timeline.add("M-I-1-1-0")
    con = _con(tmp_path)
    resumen = run(con, _cliente(api), "GOLD", 8, 3, semilla=1, aviso=lambda _m: None)
    guardadas = {f[0] for f in con.execute("SELECT match_id FROM muestra_partidas").fetchall()}
    assert "M-I-1-1-0" not in guardadas
    en_partidas = {f[0] for f in con.execute("SELECT match_id FROM partidas").fetchall()}
    assert "M-I-1-1-0" not in en_partidas
    assert resumen["partidas"] == len(guardadas) == 8


def test_jugador_con_error_se_salta_y_sigue(api, tmp_path):
    _preparar(api)
    for p in (1, 2, 3):
        for k in (1, 2):
            api.jugadores_con_error.add(f"puuid-GOLD-I-{p}-{k}")
    con = _con(tmp_path)
    resumen = run(con, _cliente(api), "GOLD", 8, 3, semilla=1, aviso=lambda _m: None)
    # División I no consigue nada; el cupo sobrante pasa a las siguientes
    assert resumen["por_division"]["I"] == 0
    assert resumen["partidas"] == 8


def test_partidas_antiguas_no_se_guardan(api, tmp_path):
    _preparar(api)
    for m in list(api.creacion):
        api.creacion[m] = HACE_60_DIAS_MS
    con = _con(tmp_path)
    resumen = run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=lambda _m: None)
    assert resumen["partidas"] == 0


def test_resumen_final_se_imprime_siempre(api, tmp_path):
    _preparar(api)
    mensajes: list[str] = []
    con = _con(tmp_path)
    run(con, _cliente(api), "GOLD", 20, 2, semilla=1, aviso=mensajes.append)
    assert mensajes[-1] == "GOLD: 20 de 20 partidas (I: 5, II: 5, III: 5, IV: 5)"


def test_no_duplica_partidas_al_repetir(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=lambda _m: None)
    n1 = con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0]
    run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=lambda _m: None)
    n2 = con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0]
    assert n2 >= n1
    ids = [f[0] for f in con.execute("SELECT match_id FROM muestra_partidas").fetchall()]
    assert len(ids) == len(set(ids))


def test_no_toca_la_base_principal(api, tmp_path):
    _preparar(api)
    principal = tmp_path / "prepartida.duckdb"
    run(_con(tmp_path), _cliente(api), "GOLD", 4, 1, semilla=1, aviso=lambda _m: None)
    assert not principal.exists()


def test_la_base_de_muestra_va_en_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(tmp_path / "mi_data"))
    cfg = leer_config()
    assert (cfg.data_dir / "muestra.duckdb").parent == tmp_path / "mi_data"


# --- R06: muestra con tope (solo lo que falta) y purga de lo viejo ---


def test_solo_descarga_lo_que_falta(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    r1 = run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=lambda _m: None)
    assert r1["partidas"] == 8
    llamadas_antes = len(api.consultas)
    mensajes: list[str] = []
    r2 = run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=mensajes.append)
    assert r2["partidas"] == 0
    assert len(api.consultas) == llamadas_antes  # ninguna llamada a la API
    assert mensajes[-1] == "GOLD: ya hay 8 partidas recientes de 8; nada que descargar"
    r3 = run(con, _cliente(api), "GOLD", 12, 2, semilla=2, aviso=lambda _m: None)
    assert r3["partidas"] == 4
    assert con.execute("SELECT count(*) FROM muestra_partidas").fetchone()[0] == 12


def test_purga_las_partidas_de_mas_de_30_dias(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    run(con, _cliente(api), "GOLD", 8, 2, semilla=1, aviso=lambda _m: None)
    vieja = con.execute("SELECT match_id FROM muestra_partidas LIMIT 1").fetchone()[0]
    con.execute(
        "UPDATE muestra_partidas SET fecha_muestra = now() - INTERVAL 40 DAY WHERE match_id = ?",
        [vieja],
    )
    api.creacion[vieja] = HACE_60_DIAS_MS  # en Riot también es vieja
    resumen = run(con, _cliente(api), "GOLD", 8, 2, semilla=3, aviso=lambda _m: None)
    assert resumen["purgadas"] == 1
    assert resumen["partidas"] == 1  # repone la purgada
    for tabla in ("muestra_partidas", "partidas", "participantes", "cuadros", "eventos"):
        n = con.execute(f"SELECT count(*) FROM {tabla} WHERE match_id = ?", [vieja]).fetchone()[0]
        assert n == 0, tabla


def test_la_purga_no_toca_otros_tiers(api, tmp_path):
    _preparar(api)
    con = _con(tmp_path)
    run(con, _cliente(api), "GOLD", 4, 1, semilla=1, aviso=lambda _m: None)
    con.execute("UPDATE muestra_partidas SET tier_muestra = 'SILVER', fecha_muestra = now() - INTERVAL 40 DAY")
    resumen = run(con, _cliente(api), "GOLD", 4, 1, semilla=1, aviso=lambda _m: None)
    assert resumen["purgadas"] == 0
    assert con.execute("SELECT count(*) FROM muestra_partidas WHERE tier_muestra = 'SILVER'").fetchone()[0] == 4
