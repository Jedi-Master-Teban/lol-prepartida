"""Pruebas de D01 (fichas de campeones). Escritas por el supervisor: no las edites."""

from __future__ import annotations

import json
import tomllib

import pytest

from prepartida import cli, conocimiento


def _campeon(id_: str, ataque: int, magia: int, alcance: int, etiquetas: list[str]) -> dict:
    return {
        "id": id_,
        "name": id_,
        "tags": etiquetas,
        "info": {"attack": ataque, "defense": 4, "magic": magia, "difficulty": 5},
        "stats": {"attackrange": alcance},
    }


def _dd(*campeones: dict) -> dict:
    return {"type": "champion", "version": "16.22.1", "data": {c["id"]: c for c in campeones}}


AHRI = _campeon("Ahri", 3, 8, 550, ["Mage", "Assassin"])
AATROX = _campeon("Aatrox", 8, 3, 175, ["Fighter"])
CAMPOS_AUTO = {"dano", "alcance", "etiquetas_riot"}
CAMPOS_CURADOS = {"enganche", "control", "escala", "arquetipo"}


@pytest.mark.parametrize(
    "ataque, magia, esperado",
    [
        (8, 3, "fisico"),
        (3, 8, "magico"),
        (5, 5, "mixto"),
        (5, 8, "magico"),  # magia = ataque + 3 justo en el límite
        (5, 7, "mixto"),  # magia = ataque + 2
        (8, 5, "fisico"),  # ataque = magia + 3 justo en el límite
        (7, 5, "mixto"),  # ataque = magia + 2
    ],
)
def test_clasificar_dano(ataque, magia, esperado):
    assert conocimiento.clasificar_dano(ataque, magia) == esperado


@pytest.mark.parametrize(
    "rango, esperado",
    [(125, "cuerpo"), (300, "cuerpo"), (301, "distancia"), (550, "distancia")],
)
def test_clasificar_alcance(rango, esperado):
    assert conocimiento.clasificar_alcance(rango) == esperado


def test_generar_ficha_nueva_tiene_exactamente_estos_campos():
    fichas = conocimiento.generar_fichas(_dd(AHRI))
    assert fichas["Ahri"] == {
        "dano": "magico",
        "alcance": "distancia",
        "etiquetas_riot": ["Mage", "Assassin"],
        "enganche": "",
        "control": "",
        "escala": "",
        "arquetipo": "",
        "verificado": False,
    }


def test_generar_incluye_todos_los_campeones():
    fichas = conocimiento.generar_fichas(_dd(AHRI, AATROX))
    assert set(fichas) == {"Ahri", "Aatrox"}


def test_regenerar_conserva_lo_curado_y_recalcula_lo_automatico():
    existentes = {
        "Ahri": {
            "dano": "fisico",  # viejo: debe recalcularse
            "alcance": "cuerpo",  # viejo: debe recalcularse
            "etiquetas_riot": ["Viejo"],
            "enganche": 1,
            "control": 2,
            "escala": "medio",
            "arquetipo": "mago_control",
            "verificado": True,
            "fuente": "borrador NIM",
        }
    }
    ficha = conocimiento.generar_fichas(_dd(AHRI), existentes)["Ahri"]
    assert ficha["dano"] == "magico"
    assert ficha["alcance"] == "distancia"
    assert ficha["etiquetas_riot"] == ["Mage", "Assassin"]
    assert ficha["enganche"] == 1
    assert ficha["control"] == 2
    assert ficha["escala"] == "medio"
    assert ficha["arquetipo"] == "mago_control"
    assert ficha["verificado"] is True
    assert ficha["fuente"] == "borrador NIM"


def test_regenerar_no_borra_entradas_que_ya_no_estan_en_data_dragon():
    existentes = {"Viejo": {"dano": "mixto", "enganche": 3, "verificado": True}}
    fichas = conocimiento.generar_fichas(_dd(AHRI), existentes)
    assert fichas["Viejo"] == {"dano": "mixto", "enganche": 3, "verificado": True}
    assert "Ahri" in fichas


def test_generar_no_modifica_las_entradas_recibidas():
    existentes = {"Ahri": {"enganche": 2, "verificado": True}}
    copia = json.loads(json.dumps(existentes))
    conocimiento.generar_fichas(_dd(AHRI), existentes)
    assert existentes == copia


def test_ida_y_vuelta_del_archivo_toml(tmp_path):
    fichas = conocimiento.generar_fichas(_dd(AHRI, AATROX))
    fichas["Ahri"].update(
        enganche=2,
        control=1,
        escala="tardio",
        arquetipo="mago_poke",
        verificado=True,
        fuente='dijo "hola" \\ y ñandú',
    )
    ruta = tmp_path / "carpeta_nueva" / "campeones.toml"
    conocimiento.escribir_fichas(fichas, ruta)
    assert conocimiento.leer_fichas(ruta) == fichas
    assert tomllib.loads(ruta.read_text(encoding="utf-8")) == fichas


def test_escribir_es_estable_y_empieza_con_un_comentario(tmp_path):
    fichas = conocimiento.generar_fichas(_dd(AHRI, AATROX))
    ruta = tmp_path / "c.toml"
    conocimiento.escribir_fichas(fichas, ruta)
    primero = ruta.read_bytes()
    conocimiento.escribir_fichas(conocimiento.leer_fichas(ruta), ruta)
    assert ruta.read_bytes() == primero
    assert primero.decode("utf-8").startswith("# ")
    texto = primero.decode("utf-8")
    assert texto.index("[Aatrox]") < texto.index("[Ahri]")  # orden alfabético


def test_leer_fichas_de_archivo_inexistente_da_diccionario_vacio(tmp_path):
    assert conocimiento.leer_fichas(tmp_path / "no_existe.toml") == {}


def _preparar_estaticos(tmp_path, monkeypatch):
    for version, campeones in (("16.9.1", [AATROX]), ("16.22.1", [AHRI, AATROX])):
        carpeta = tmp_path / "data" / "estaticos" / version
        carpeta.mkdir(parents=True)
        (carpeta / "champion.json").write_text(json.dumps(_dd(*campeones)), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(tmp_path / "data"))


def test_version_mas_reciente_compara_numeros_no_texto(tmp_path, monkeypatch):
    _preparar_estaticos(tmp_path, monkeypatch)
    assert conocimiento.version_mas_reciente(tmp_path / "data" / "estaticos") == "16.22.1"


def test_version_mas_reciente_sin_datos_da_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        conocimiento.version_mas_reciente(tmp_path / "vacio")


def test_comando_generar_escribe_y_conserva_lo_curado(tmp_path, monkeypatch, capsys):
    _preparar_estaticos(tmp_path, monkeypatch)
    assert cli.main(["conocimiento", "--generar"]) == 0
    destino = tmp_path / "conocimiento" / "campeones.toml"
    fichas = conocimiento.leer_fichas(destino)
    assert set(fichas) == {"Ahri", "Aatrox"}  # usa la versión 16.22.1, no la 16.9.1
    assert "campeones" in capsys.readouterr().out

    fichas["Ahri"].update(enganche=2, verificado=True)
    conocimiento.escribir_fichas(fichas, destino)
    assert cli.main(["conocimiento", "--generar"]) == 0
    despues = conocimiento.leer_fichas(destino)
    assert despues["Ahri"]["enganche"] == 2
    assert despues["Ahri"]["verificado"] is True


def test_comando_generar_sin_datos_estaticos_avisa(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(tmp_path / "data"))
    assert cli.main(["conocimiento", "--generar"]) == 2
    assert "estaticos" in capsys.readouterr().err
