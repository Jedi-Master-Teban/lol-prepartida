from __future__ import annotations

import json

import httpx
import pytest

from prepartida import db, exportar, ingest
from prepartida.perfil import Perfil
from prepartida.riot_client import RateLimiter, RiotClient

PERFIL = Perfil(pool=("Ahri",), partidas_por_sesion=2)
VERSION = "16.22.1"
ARCHIVOS = ("meta.json", "partidas.json", "curvas.json", "muertes.json", "compras.json", "estaticos.json")
CAMPOS_PARTIDA = {
    "match_id", "inicio", "dia_sesion", "n_del_dia", "parche", "champion_id", "campeon",
    "posicion", "lado", "victoria", "asesinatos", "muertes", "asistencias", "duracion_min",
    "cs_min", "rival_champion_id", "rival", "cs_10", "dif_oro_10", "dif_oro_15", "muertes_14",
    "primera_muerte_min", "en_pool", "items", "hechizos", "runa_clave", "arbol_primario",
    "arbol_secundario",
}

RUNAS = [
    {
        "id": 8100,
        "name": "Dominación",
        "icon": "perk-images/Styles/7200_Domination.png",
        "slots": [
            {
                "runes": [
                    {
                        "id": 8112,
                        "name": "Electrocutar",
                        "icon": "perk-images/Styles/Domination/Electrocute/Electrocute.png",
                    }
                ]
            },
            {"runes": []},
        ],
    },
    {
        "id": 8200,
        "name": "Resolución",
        "icon": "perk-images/Styles/7200_Resolve.png",
        "slots": [
            {
                "runes": [
                    {
                        "id": 8226,
                        "name": "Maniobras",
                        "icon": "perk-images/Styles/Resolve/Maniobras/Maniobras.png",
                    }
                ]
            },
            {"runes": []},
        ],
    },
]

HECHIZOS = {
    "type": "summoner",
    "version": VERSION,
    "data": {
        "SummonerFlash": {"id": "SummonerFlash", "name": "Destello", "key": "4"},
        "SummonerDot": {"id": "SummonerDot", "name": "Ignición", "key": "14"},
    },
}


def _base(api):
    con = db.conectar()
    cliente = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    puuid = ingest.ingerir_perfil(cliente, con, "SithLordDropout", "LAN")
    ingest.ingerir_historial(cliente, con, puuid)
    return con, puuid


def _estaticos_falsos(static_dir):
    carpeta = static_dir / VERSION
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "runesReforged.json").write_text(
        json.dumps(RUNAS, ensure_ascii=False), encoding="utf-8"
    )
    (carpeta / "summoner.json").write_text(
        json.dumps(HECHIZOS, ensure_ascii=False), encoding="utf-8"
    )


def _datos_estaticos(con):
    con.executemany(
        "INSERT OR REPLACE INTO campeones VALUES (?, ?, ?, ?, ?)",
        [(103, "Ahri", "Ahri", "Mage", VERSION), (8, "Campeon8", "Campeon8", "", VERSION)],
    )
    con.executemany(
        "INSERT OR REPLACE INTO items VALUES (?, ?, ?, ?, ?)",
        [(3000 + i, f"Item{i}", 2500, "", VERSION) for i in range(7)],
    )


def _exportar(api, tmp_path):
    con, _ = _base(api)
    _estaticos_falsos(tmp_path)
    _datos_estaticos(con)
    destino = tmp_path / "data"
    conteo = exportar.exportar(con, PERFIL, tmp_path, destino)
    return con, destino, conteo


def test_exporta_los_seis_archivos(api, tmp_path):
    _, destino, conteo = _exportar(api, tmp_path)
    assert set(conteo) == {"meta", "partidas", "curvas", "muertes", "compras", "estaticos"}
    for nombre in ARCHIVOS:
        ruta = destino / nombre
        assert ruta.exists(), nombre
        json.loads(ruta.read_text(encoding="utf-8"))  # JSON válido


def test_partidas_tienen_los_campos_del_contrato(api, tmp_path):
    _, destino, conteo = _exportar(api, tmp_path)
    partidas = json.loads((destino / "partidas.json").read_text(encoding="utf-8"))
    assert conteo["partidas"] == 3
    assert len(partidas) == 3
    assert set(partidas[0]) == CAMPOS_PARTIDA
    inicios = [p["inicio"] for p in partidas]
    assert inicios == sorted(inicios)
    assert inicios[0].endswith("Z")
    assert partidas[0]["dia_sesion"] == "2026-11-06"  # inicio menos las 10 horas de desfase
    assert [p["n_del_dia"] for p in partidas] == [1, 2, 3]
    assert partidas[0]["campeon"] == "Ahri" and partidas[0]["posicion"] == "MIDDLE"
    assert partidas[0]["lado"] == "azul"
    assert partidas[0]["champion_id"] == 103 and partidas[0]["rival_champion_id"] == 8
    assert partidas[0]["rival"] == "Campeon8"
    assert partidas[0]["items"] == [3000, 3001, 3002, 3003, 3004, 3005, 3006]
    assert partidas[0]["hechizos"] == [4, 14]
    assert partidas[0]["runa_clave"] == 8112
    assert partidas[0]["arbol_primario"] == 8100 and partidas[0]["arbol_secundario"] == 8200
    assert partidas[0]["en_pool"] is True
    assert partidas[0]["victoria"] is True
    assert [p["victoria"] for p in partidas] == [True, False, True]


def test_ningun_archivo_filtra_identificadores_de_otros_jugadores(api, tmp_path):
    _, destino, _ = _exportar(api, tmp_path)
    for nombre in ARCHIVOS:
        texto = (destino / nombre).read_text(encoding="utf-8")
        assert "puuid" not in texto, nombre
        assert "otro-" not in texto, nombre


def test_curvas_con_diferencia_de_oro(api, tmp_path):
    _, destino, conteo = _exportar(api, tmp_path)
    curvas = json.loads((destino / "curvas.json").read_text(encoding="utf-8"))
    assert conteo["curvas"] == 3
    for serie in curvas.values():
        assert serie["dif_oro"][15] == 750  # 15 min x (400 - 350) de oro por minuto
        assert serie["oro"][15] == 6500
        assert serie["cs"][15] == 105  # 7 súbditos por minuto
        assert serie["dif_oro"][0] == 0
        assert len(serie["oro"]) == len(serie["cs"]) == len(serie["dif_oro"])


def test_ningun_archivo_contiene_nan(api, tmp_path):
    _, destino, _ = _exportar(api, tmp_path)
    for nombre in ARCHIVOS:
        texto = (destino / nombre).read_text(encoding="utf-8")
        assert "NaN" not in texto, nombre
        assert "NaT" not in texto, nombre


def test_meta_con_jugador_rango_y_perfil(api, tmp_path):
    _, destino, _ = _exportar(api, tmp_path)
    meta = json.loads((destino / "meta.json").read_text(encoding="utf-8"))
    assert meta["jugador"]["game_name"] == "SithLordDropout"
    assert meta["jugador"]["tag_line"] == "LAN"
    assert meta["jugador"]["tier"] == "BRONZE"
    assert meta["jugador"]["division"] == "III"
    assert meta["jugador"]["lp"] == 40
    assert meta["jugador"]["victorias"] == 30 and meta["jugador"]["derrotas"] == 32
    assert meta["version_ddragon"] == VERSION
    assert meta["perfil"]["pool"] == ["Ahri"]
    assert meta["perfil"]["meta_cs_10"] == 70
    assert meta["perfil"]["desfase_horas"] == 10
    assert meta["generado"].endswith("Z")


def test_muertes_solo_con_posicion(api, tmp_path):
    con, destino, conteo = _exportar(api, tmp_path)
    # El evento simulado mata al participante 8; se cambia la víctima al jugador (3).
    con.execute(
        "UPDATE eventos SET detalle = replace(detalle::VARCHAR, '\"victimId\": 8', '\"victimId\": 3')"
    )
    con.execute(
        "INSERT INTO eventos VALUES (?, ?, ?, ?, ?)",
        [
            "LA1_1",
            420000,
            "CHAMPION_KILL",
            8,
            json.dumps(
                {
                    "type": "CHAMPION_KILL",
                    "timestamp": 420000,
                    "killerId": 8,
                    "victimId": 3,
                    "position": {"x": 7200, "y": 7450},
                }
            ),
        ],
    )
    destino.mkdir(parents=True, exist_ok=True)
    conteo = exportar.exportar(con, PERFIL, tmp_path, destino)
    muertes = json.loads((destino / "muertes.json").read_text(encoding="utf-8"))
    # El evento simulado no trae posición, así que solo cuenta el que la trae.
    assert conteo["muertes"] == 1
    assert muertes == [{"match_id": "LA1_1", "minuto": 7.0, "x": 7200, "y": 7450}]


def test_compras_solo_de_items_completos(api, tmp_path):
    con, destino, _ = _exportar(api, tmp_path)
    con.execute(
        "INSERT INTO eventos VALUES (?, ?, ?, ?, ?)",
        [
            "LA1_1",
            600000,
            "ITEM_PURCHASED",
            3,
            json.dumps({"type": "ITEM_PURCHASED", "timestamp": 600000, "participantId": 3, "itemId": 3000}),
        ],
    )
    con.execute(
        "INSERT INTO eventos VALUES (?, ?, ?, ?, ?)",
        [
            "LA1_1",
            120000,
            "ITEM_PURCHASED",
            3,
            json.dumps({"type": "ITEM_PURCHASED", "timestamp": 120000, "participantId": 3, "itemId": 3001}),
        ],
    )
    destino.mkdir(parents=True, exist_ok=True)
    conteo = exportar.exportar(con, PERFIL, tmp_path, destino)
    compras = json.loads((destino / "compras.json").read_text(encoding="utf-8"))
    assert conteo["compras"] == 2
    assert compras["LA1_1"] == [
        {"minuto": 2.0, "item_id": 3001},
        {"minuto": 10.0, "item_id": 3000},
    ]


def test_estaticos_solo_los_referenciados(api, tmp_path):
    _, destino, conteo = _exportar(api, tmp_path)
    estaticos = json.loads((destino / "estaticos.json").read_text(encoding="utf-8"))
    assert estaticos["campeones"]["103"] == {"clave": "Ahri", "nombre": "Ahri"}
    assert estaticos["campeones"]["8"]["clave"] == "Campeon8"
    assert estaticos["items"]["3000"] == {"nombre": "Item0"}
    assert estaticos["runas"]["8112"]["nombre"] == "Electrocutar"
    assert estaticos["runas"]["8112"]["icono"].endswith("Electrocute.png")
    assert estaticos["arboles"]["8100"]["nombre"] == "Dominación"
    assert estaticos["hechizos"]["4"] == {"clave": "SummonerFlash", "nombre": "Destello"}
    assert estaticos["hechizos"]["14"]["nombre"] == "Ignición"
    # Solo lo referenciado: la runa 8226 no es la runa clave de ninguna partida.
    assert "8226" not in estaticos["runas"]
    assert conteo["estaticos"] == sum(len(v) for v in estaticos.values())


def test_estaticos_incluye_items_de_compras(api, tmp_path):
    con, destino, _ = _exportar(api, tmp_path)
    con.execute(
        "INSERT OR REPLACE INTO items VALUES (9999, 'Ítem raro', 3000, '', ?)", [VERSION]
    )
    con.execute(
        "INSERT INTO eventos VALUES (?, ?, ?, ?, ?)",
        [
            "LA1_1",
            600000,
            "ITEM_PURCHASED",
            3,
            json.dumps(
                {
                    "type": "ITEM_PURCHASED",
                    "timestamp": 600000,
                    "participantId": 3,
                    "itemId": 9999,
                }
            ),
        ],
    )
    destino.mkdir(parents=True, exist_ok=True)
    exportar.exportar(con, PERFIL, tmp_path, destino)
    estaticos = json.loads((destino / "estaticos.json").read_text(encoding="utf-8"))
    assert estaticos["items"]["9999"] == {"nombre": "Ítem raro"}


def test_sin_jugador_da_error(tmp_path):
    con = db.conectar()
    with pytest.raises(ValueError, match="No hay jugador en la base"):
        exportar.exportar(con, PERFIL, tmp_path, tmp_path / "salida")


def test_no_exporta_si_el_jugador_no_tiene_partidas(api, tmp_path):
    """Protege la página: nunca se publican archivos vacíos por un jugador sin partidas."""
    con, _ = _base(api)
    _estaticos_falsos(tmp_path / "estaticos")
    con.execute("UPDATE participantes SET puuid = 'otro' WHERE puuid = 'puuid-yo'")
    destino = tmp_path / "data"
    with pytest.raises(ValueError, match="sin partidas"):
        exportar.exportar(con, PERFIL, tmp_path / "estaticos", destino)
    assert not (destino / "partidas.json").exists()
