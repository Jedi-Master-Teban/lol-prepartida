"""Pruebas de D04a (intérprete de reglas). Escritas por el supervisor: no las edites."""

from __future__ import annotations

from pathlib import Path

import pytest

from prepartida import composicion, reglas

CTX = {
    "enemigo": {"prop_fisico": 0.75, "control_total": 4, "escala_dominante": "tardio"},
    "aliado": {"prop_fisico": 0.2, "n_conocidos": 5},
    "contraste": {"mejor_escala": "aliado", "enemigo_un_tipo_dano": True, "dif_enganche": -2},
}


@pytest.mark.parametrize(
    "condicion, esperado",
    [
        ("enemigo.prop_fisico >= 0.7", True),
        ("enemigo.prop_fisico >= 0.75", True),
        ("enemigo.prop_fisico > 0.75", False),
        ("enemigo.prop_fisico <= 0.7", False),
        ("enemigo.prop_fisico < 0.8", True),
        ("enemigo.control_total == 4", True),
        ("enemigo.control_total != 4", False),
        ('contraste.mejor_escala == "aliado"', True),
        ('contraste.mejor_escala != "aliado"', False),
        ("contraste.enemigo_un_tipo_dano == true", True),
        ("contraste.enemigo_un_tipo_dano == false", False),
        ("contraste.dif_enganche <= -2", True),
        ("contraste.dif_enganche < -2", False),
        ("enemigo.prop_fisico >= 0.7 and aliado.n_conocidos >= 5", True),
        ("enemigo.prop_fisico >= 0.7 and aliado.n_conocidos >= 6", False),
        ("  enemigo.control_total   >=   3  and  aliado.prop_fisico < 0.5 and contraste.dif_enganche < 0", True),
        ("0.5 < enemigo.prop_fisico", True),  # el campo puede ir a la derecha
    ],
)
def test_evaluar_condicion(condicion, esperado):
    assert reglas.evaluar_condicion(condicion, CTX) is esperado


@pytest.mark.parametrize(
    "condicion",
    [
        "",
        "   ",
        "enemigo.no_existe >= 1",  # campo que no existe
        "otro.prop_fisico >= 1",  # grupo que no existe
        "enemigo.prop_fisico",  # sin comparación
        "enemigo.prop_fisico ~ 1",  # operador desconocido
        "enemigo.prop_fisico >= 0.7 or aliado.n_conocidos >= 5",  # 'or' no existe
        "enemigo.prop_fisico >= 0.7 and",  # 'and' colgando
        "(enemigo.prop_fisico >= 0.7)",  # paréntesis no permitidos
        "__import__('os').system('ls') == 1",  # nada de código
        "enemigo.prop_fisico >= 0.7; import os",
        'contraste.mejor_escala >= 3',  # texto contra número
        'enemigo.control_total == "4"',  # número contra texto
    ],
)
def test_condicion_invalida_da_value_error(condicion):
    with pytest.raises(ValueError):
        reglas.evaluar_condicion(condicion, CTX)


def _escribir(tmp_path: Path, cuerpo: str) -> Path:
    ruta = tmp_path / "briefing.toml"
    ruta.write_text(cuerpo, encoding="utf-8")
    return ruta


REGLA_OK = """
[pesos]
tasa_ajustada = 1.0
encaje_equipo = 2

[[regla]]
id = "uno"
si = "enemigo.prop_fisico >= 0.7"
hecho = "Hecho uno."
categoria = "compras"

[[regla]]
id = "dos"
si = "contraste.mejor_escala == \\"aliado\\""
hecho = "Hecho dos."
categoria = "victoria"

[[regla]]
id = "tres"
si = "enemigo.control_total >= 9"
hecho = "Hecho tres."
categoria = "mapa"
"""


def test_cargar_reglas_devuelve_pesos_y_reglas(tmp_path):
    cargado = reglas.cargar_reglas(_escribir(tmp_path, REGLA_OK))
    assert set(cargado) == {"pesos", "reglas"}
    assert cargado["pesos"] == {"tasa_ajustada": 1.0, "encaje_equipo": 2.0}
    assert [r["id"] for r in cargado["reglas"]] == ["uno", "dos", "tres"]


def test_reglas_aplicables_filtra_y_conserva_el_orden(tmp_path):
    cargado = reglas.cargar_reglas(_escribir(tmp_path, REGLA_OK))
    aplicables = reglas.reglas_aplicables(cargado["reglas"], CTX)
    assert aplicables == [
        {"id": "uno", "hecho": "Hecho uno.", "categoria": "compras"},
        {"id": "dos", "hecho": "Hecho dos.", "categoria": "victoria"},
    ]


@pytest.mark.parametrize(
    "cambio, texto_del_error",
    [
        ('hecho = "Hecho uno."\n', "uno"),  # se quita 'hecho'
        ('categoria = "compras"\n', "uno"),  # se quita 'categoria'
        ('si = "enemigo.prop_fisico >= 0.7"\n', "uno"),  # se quita 'si'
    ],
)
def test_regla_con_campo_faltante_da_error_con_el_id(tmp_path, cambio, texto_del_error):
    with pytest.raises(ValueError, match=texto_del_error):
        reglas.cargar_reglas(_escribir(tmp_path, REGLA_OK.replace(cambio, "", 1)))


def test_categoria_invalida_da_error(tmp_path):
    malo = REGLA_OK.replace('categoria = "compras"', 'categoria = "inventada"')
    with pytest.raises(ValueError, match="uno"):
        reglas.cargar_reglas(_escribir(tmp_path, malo))


def test_id_repetido_da_error(tmp_path):
    malo = REGLA_OK.replace('id = "dos"', 'id = "uno"')
    with pytest.raises(ValueError, match="uno"):
        reglas.cargar_reglas(_escribir(tmp_path, malo))


def test_condicion_con_sintaxis_invalida_se_detecta_al_cargar(tmp_path):
    malo = REGLA_OK.replace("enemigo.prop_fisico >= 0.7", "enemigo.prop_fisico ~ 0.7")
    with pytest.raises(ValueError, match="uno"):
        reglas.cargar_reglas(_escribir(tmp_path, malo))


def test_peso_que_no_es_numero_da_error(tmp_path):
    malo = REGLA_OK.replace("tasa_ajustada = 1.0", 'tasa_ajustada = "alto"')
    with pytest.raises(ValueError, match="tasa_ajustada"):
        reglas.cargar_reglas(_escribir(tmp_path, malo))


def test_archivo_sin_pesos_da_pesos_vacios(tmp_path):
    sin_pesos = REGLA_OK.split("[[regla]]", 1)[1]
    cargado = reglas.cargar_reglas(_escribir(tmp_path, "[[regla]]" + sin_pesos))
    assert cargado["pesos"] == {}
    assert len(cargado["reglas"]) == 3


RAIZ = Path(__file__).resolve().parents[1]


def test_el_archivo_real_carga_y_solo_usa_campos_que_existen():
    cargado = reglas.cargar_reglas(RAIZ / "reglas" / "briefing.toml")
    assert len(cargado["reglas"]) >= 8
    vacio = composicion.construir_contexto([], [], {})
    reglas.reglas_aplicables(cargado["reglas"], vacio)  # no debe lanzar error


def test_el_archivo_real_dispara_la_regla_de_enemigo_fisico():
    cargado = reglas.cargar_reglas(RAIZ / "reglas" / "briefing.toml")
    fichas = {
        n: {"dano": "fisico", "alcance": "distancia", "etiquetas_riot": [], "enganche": 0,
            "control": 0, "escala": "medio", "arquetipo": "tirador", "verificado": True}
        for n in "ABCDE"
    }
    ctx = composicion.construir_contexto([], list("ABCDE"), fichas)
    ids = [r["id"] for r in reglas.reglas_aplicables(cargado["reglas"], ctx)]
    assert "enemigo_fisico" in ids
    assert "enemigo_magico" not in ids
