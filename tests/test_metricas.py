from __future__ import annotations

from datetime import datetime

import httpx

from prepartida import db, ingest, metricas
from prepartida.perfil import Perfil, leer_perfil
from prepartida.riot_client import RateLimiter, RiotClient

PERFIL = Perfil(pool=("Ahri",), partidas_por_sesion=2)


def _base(api):
    con = db.conectar()
    c = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    puuid = ingest.ingerir_perfil(c, con, "SithLordDropout", "LAN")
    ingest.ingerir_historial(c, con, puuid)
    return con, puuid


def test_tasa_ajustada():
    assert round(metricas.tasa_ajustada(2, 3), 1) == 53.8
    assert metricas.tasa_ajustada(0, 0) == 50.0


def test_metricas_por_partida(api):
    con, puuid = _base(api)
    df = metricas.partidas_del_jugador(con, puuid, PERFIL)
    assert len(df) == 3
    fila = df.iloc[0]
    assert fila["campeon"] == "Ahri" and fila["rival"] == "Campeon8"
    assert fila["cs_10"] == 70  # 7 súbditos por minuto en la API simulada
    assert fila["dif_oro_10"] == 500 and fila["dif_oro_15"] == 750
    assert fila["muertes_14"] == 0 and bool(fila["en_pool"])
    # Las tres partidas simuladas empiezan a la misma hora: mismo día de sesión.
    assert sorted(df["n_del_dia"]) == [1, 2, 3]


def test_muertes_tempranas_cuentan_solo_las_propias(api):
    con, puuid = _base(api)
    # El evento simulado es una muerte del participante 8 a manos del 3 (yo).
    con.execute("UPDATE eventos SET detalle = replace(detalle::VARCHAR, '\"victimId\": 8', '\"victimId\": 3')")
    df = metricas.partidas_del_jugador(con, puuid, PERFIL)
    assert list(df["muertes_14"]) == [1, 1, 1]
    assert round(df["primera_muerte_min"].iloc[0], 1) == 5.0


def test_agregados(api):
    con, puuid = _base(api)
    df = metricas.partidas_del_jugador(con, puuid, PERFIL)
    campeones = metricas.por_campeon(df)
    assert campeones.iloc[0][["campeon", "partidas", "victorias"]].tolist() == ["Ahri", 3, 2]
    assert campeones.iloc[0]["tasa_ajustada"] == 53.8
    pvf = metricas.pool_vs_fuera(df)
    assert pvf.loc["En el pool", "partidas"] == 3 and "Fuera del pool" not in pvf.index
    sesion = metricas.por_orden_en_sesion(df, 2)
    assert sesion.loc["Partidas 1 a 2 del día", "partidas"] == 2
    assert sesion.loc["Partida 3 en adelante", "partidas"] == 1
    r = metricas.resumen(df)
    assert r["partidas"] == 3 and r["por_detras_15"] == 0 and r["con_dato_15"] == 3


def test_partidas_de_hoy(api):
    con, puuid = _base(api)
    df = metricas.partidas_del_jugador(con, puuid, PERFIL)
    inicio = df["inicio"].iloc[0].to_pydatetime()
    assert len(metricas.partidas_de_hoy(df, PERFIL, ahora=inicio)) == 3
    assert len(metricas.partidas_de_hoy(df, PERFIL, ahora=datetime(2030, 1, 1))) == 0


def test_leer_perfil(tmp_path):
    ruta = tmp_path / "perfil.toml"
    ruta.write_text('pool = ["Ahri", "Sylas"]\n[metas]\ncs_10 = 65\n', encoding="utf-8")
    p = leer_perfil(ruta)
    assert p.pool == ("Ahri", "Sylas") and p.meta_cs_10 == 65 and p.partidas_por_sesion == 3
    assert leer_perfil(tmp_path / "no-existe.toml") == Perfil()


# --- R03: métricas para cualquier participante ---

CINCO = ["cs_10", "dif_oro_10", "dif_oro_15", "muertes_14"]


def test_por_rol_coincide_con_partidas_del_jugador(api):
    """Regresión: las filas del jugador son idénticas en ambas funciones."""
    con, puuid = _base(api)
    con.execute("UPDATE eventos SET detalle = replace(detalle::VARCHAR, '\"victimId\": 8', '\"victimId\": 3')")
    propio = metricas.partidas_del_jugador(con, puuid, PERFIL).sort_values("match_id")
    rol = metricas.metricas_por_rol(con, posiciones=("MIDDLE",))
    mio = rol[rol["puuid"] == puuid].sort_values("match_id")
    assert list(mio["match_id"]) == list(propio["match_id"])
    for col in ["campeon", "posicion", "parche", "victoria"] + CINCO:
        assert list(mio[col]) == list(propio[col]), col


def test_por_rol_incluye_ambos_equipos_y_solo_los_roles_pedidos(api):
    con, _ = _base(api)
    rol = metricas.metricas_por_rol(con)
    assert set(rol["posicion"]) == {"MIDDLE", "BOTTOM"}
    # 3 partidas x 2 roles x 2 equipos
    assert len(rol) == 12
    assert set(rol.columns) >= {
        "match_id", "posicion", "campeon", "victoria", "cs_10", "dif_oro_10",
        "dif_oro_15", "muertes_14", "parche", "tier_muestra",
    }
    # Rivales espejo: la diferencia de oro de uno es la del otro con signo cambiado.
    p = rol[(rol["match_id"] == "LA1_1") & (rol["posicion"] == "MIDDLE")]
    assert sorted(p["dif_oro_10"]) == [-500, 500]


def test_por_rol_agrega_tier_si_existe_la_tabla_de_muestra(api):
    con, _ = _base(api)
    assert metricas.metricas_por_rol(con)["tier_muestra"].isna().all()
    con.execute("CREATE TABLE muestra_partidas (match_id VARCHAR, tier_muestra VARCHAR, fecha_muestra TIMESTAMP)")
    con.execute("INSERT INTO muestra_partidas VALUES ('LA1_1', 'GOLD', now())")
    rol = metricas.metricas_por_rol(con)
    assert set(rol.loc[rol["match_id"] == "LA1_1", "tier_muestra"]) == {"GOLD"}
    assert rol.loc[rol["match_id"] != "LA1_1", "tier_muestra"].isna().all()


def test_por_rol_quita_partidas_de_menos_de_5_minutos(api):
    con, _ = _base(api)
    con.execute("UPDATE partidas SET duracion_s = 240 WHERE match_id = 'LA1_1'")
    rol = metricas.metricas_por_rol(con)
    assert "LA1_1" not in set(rol["match_id"])
    assert len(rol) == 8


def test_por_rol_sin_metricas_a_los_15_en_partidas_cortas(api):
    con, _ = _base(api)
    con.execute("UPDATE partidas SET duracion_s = 780 WHERE match_id = 'LA1_1'")
    rol = metricas.metricas_por_rol(con)
    corta = rol[rol["match_id"] == "LA1_1"]
    assert len(corta) == 4
    assert corta["dif_oro_15"].isna().all() and corta["muertes_14"].isna().all()
    assert corta["cs_10"].notna().all()  # lo de los 10 minutos se conserva
    larga = rol[rol["match_id"] != "LA1_1"]
    assert larga["dif_oro_15"].notna().all() and larga["muertes_14"].notna().all()
