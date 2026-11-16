from __future__ import annotations

import httpx
import pytest

from prepartida import db, ddragon, estado, ingest, parse
from prepartida.riot_client import ClaveInvalida, RateLimiter, RiotClient

from conftest import PUUID, linea_falsa, partida_falsa


class Reloj:
    def __init__(self) -> None:
        self.t = 0.0
        self.esperas: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.esperas.append(s)
        self.t += s


def cliente(api, clave="clave-buena", reloj: Reloj | None = None) -> RiotClient:
    reloj = reloj or Reloj()
    return RiotClient(
        clave,
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(clock=reloj.now, sleep=reloj.sleep),
        sleep=reloj.sleep,
    )


def test_limitador_respeta_la_ventana_corta():
    reloj = Reloj()
    lim = RateLimiter(limites=((2, 1.0),), clock=reloj.now, sleep=reloj.sleep)
    lim.acquire()
    lim.acquire()
    assert reloj.esperas == []
    lim.acquire()
    assert reloj.esperas == [1.0]


def test_limitador_respeta_la_ventana_larga():
    reloj = Reloj()
    lim = RateLimiter(limites=((20, 1.0), (100, 120.0)), clock=reloj.now, sleep=reloj.sleep)
    for _ in range(101):
        lim.acquire()
    # 100 peticiones caben en ~4 s; la 101 debe esperar al cierre de los 2 minutos.
    assert reloj.t >= 120.0


def test_enrutamiento_regional_y_de_plataforma(api):
    c = cliente(api)
    c.cuenta_por_riot_id("SithLordDropout", "LAN")
    c.ligas_por_puuid(PUUID)
    assert api.llamadas[0].startswith("americas.api.riotgames.com/riot/account/v1/")
    assert api.llamadas[1].startswith("la1.api.riotgames.com/lol/league/v4/")


def test_reintenta_tras_429_usando_retry_after(api):
    reloj = Reloj()
    api.fallos_429 = 2
    c = cliente(api, reloj=reloj)
    assert c.cuenta_por_riot_id("SithLordDropout", "LAN")["puuid"] == PUUID
    assert reloj.esperas.count(3.0) == 2


def test_clave_rechazada_da_error_claro(api):
    c = cliente(api, clave="clave-vencida")
    with pytest.raises(ClaveInvalida):
        c.cuenta_por_riot_id("SithLordDropout", "LAN")


def test_clave_vacia_falla_antes_de_llamar():
    with pytest.raises(ClaveInvalida):
        RiotClient("")


def test_parseo_de_partida_y_linea_de_tiempo():
    partida = partida_falsa("LA1_9", gano=True)
    fila = parse.fila_partida(partida)
    assert fila[0] == "LA1_9" and fila[2] == "16.22" and fila[6] is True
    participantes = parse.filas_participantes(partida)
    assert len(participantes) == 10
    yo = participantes[2]
    assert yo[3] == "azul" and yo[5] == "Ahri" and yo[6] == "MIDDLE" and yo[11] == 190
    assert yo[-3:] == (8112, 8100, 8200)
    linea = linea_falsa("LA1_9")
    assert len(parse.filas_cuadros(linea)) == 17 * 10
    eventos = parse.filas_eventos(linea)
    assert eventos[0][2] == "CHAMPION_KILL" and eventos[0][3] == 3


def test_ingesta_completa_y_reingesta_sin_duplicar(api, tmp_path):
    con = db.conectar()
    c = cliente(api)
    puuid = ingest.ingerir_perfil(c, con, "SithLordDropout", "LAN")
    r = ingest.ingerir_historial(c, con, puuid, max_partidas=50, raw_dir=tmp_path)
    assert r == {"encontradas": 3, "nuevas": 3, "sin_linea_de_tiempo": 0}
    assert con.execute("SELECT count(*) FROM participantes").fetchone()[0] == 30
    assert (tmp_path / "LA1_1.json.gz").exists()
    assert (tmp_path / "LA1_1_timeline.json.gz").exists()

    antes = len(api.llamadas)
    r2 = ingest.ingerir_historial(c, con, puuid, max_partidas=50)
    assert r2["nuevas"] == 0
    # Solo se piden las listas de IDs, no se vuelven a descargar partidas.
    assert all(ll.endswith("/ids") for ll in api.llamadas[antes:])
    assert con.execute("SELECT count(*) FROM eventos").fetchone()[0] == 3


def test_estado_resume_por_campeon(api):
    con = db.conectar()
    c = cliente(api)
    puuid = ingest.ingerir_perfil(c, con, "SithLordDropout", "LAN")
    ingest.ingerir_historial(c, con, puuid)
    filas = estado.por_campeon(con, puuid)
    assert len(filas) == 1
    campeon, pos, n, v, tasa, ajustada, kda, cs_min, dif = filas[0]
    assert (campeon, pos, n, v) == ("Ahri", "MIDDLE", 3, 2)
    assert tasa == 66.7
    assert ajustada == 53.8  # (2 + 5) / (3 + 10)
    assert kda == 6.0
    assert cs_min == 6.3  # 190 CS en 30 minutos
    assert dif == 750  # 15 min x (400 - 350) de oro por minuto
    salida = estado.texto(con)
    assert "BRONZE III" in salida and "Ahri" in salida


def test_data_dragon_descarga_y_carga(tmp_path):
    def falso(request: httpx.Request) -> httpx.Response:
        ruta = request.url.path
        if ruta.endswith("versions.json"):
            return httpx.Response(200, json=["16.22.1", "16.21.1"])
        if ruta.endswith("champion.json"):
            assert "/16.22.1/data/es_MX/" in ruta
            return httpx.Response(
                200,
                json={"data": {"Ahri": {"key": "103", "id": "Ahri", "name": "Ahri", "tags": ["Mage", "Assassin"]}}},
            )
        if ruta.endswith("item.json"):
            return httpx.Response(
                200, json={"data": {"3157": {"name": "Reloj de Arena de Zhonya", "gold": {"total": 3250}, "tags": ["Armor"]}}}
            )
        return httpx.Response(200, json={})

    version, datos = ddragon.descargar(tmp_path, transport=httpx.MockTransport(falso))
    assert version == "16.22.1"
    assert (tmp_path / "16.22.1" / "runesReforged.json").exists()
    con = db.conectar()
    assert ddragon.cargar_en_db(con, version, datos) == {"campeones": 1, "items": 1}
    assert con.execute("SELECT nombre FROM campeones WHERE champion_id = 103").fetchone()[0] == "Ahri"
