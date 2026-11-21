"""Pruebas de D03 (perfil de una composición). Escritas por el supervisor: no las edites."""

from __future__ import annotations

import pytest

from prepartida import composicion


def ficha(dano="fisico", alcance="distancia", enganche=0, control=0, escala="medio",
          arquetipo="tirador", verificado=True) -> dict:
    return {
        "dano": dano,
        "alcance": alcance,
        "etiquetas_riot": [],
        "enganche": enganche,
        "control": control,
        "escala": escala,
        "arquetipo": arquetipo,
        "verificado": verificado,
    }


CLAVES_PERFIL = {
    "prop_fisico", "prop_magico", "enganche_total", "control_total", "escala_dominante",
    "arquetipos", "n_cuerpo", "n_conocidos", "desconocidos",
}
CLAVES_CONTRASTE = {
    "dif_enganche", "dif_control", "mas_enganche", "mas_control", "mejor_escala",
    "enemigo_casi_todo_fisico", "enemigo_casi_todo_magico", "enemigo_un_tipo_dano",
}


def test_equipo_vacio():
    p = composicion.perfil_equipo([], {})
    assert set(p) == CLAVES_PERFIL
    assert p["prop_fisico"] == 0.0
    assert p["prop_magico"] == 0.0
    assert p["enganche_total"] == 0
    assert p["control_total"] == 0
    assert p["escala_dominante"] == ""
    assert p["arquetipos"] == []
    assert p["n_cuerpo"] == 0
    assert p["n_conocidos"] == 0
    assert p["desconocidos"] == []


def test_proporciones_de_dano_mixto_cuenta_mitad_y_mitad():
    fichas = {
        "A": ficha(dano="fisico"),
        "B": ficha(dano="fisico"),
        "C": ficha(dano="magico"),
        "D": ficha(dano="mixto"),
    }
    p = composicion.perfil_equipo(["A", "B", "C", "D"], fichas)
    assert p["prop_fisico"] == pytest.approx(0.625)
    assert p["prop_magico"] == pytest.approx(0.375)
    assert p["n_conocidos"] == 4


def test_sin_ficha_o_sin_verificar_es_desconocido_y_no_cuenta():
    fichas = {"A": ficha(dano="magico", enganche=3), "B": ficha(dano="fisico", enganche=3, verificado=False)}
    p = composicion.perfil_equipo(["A", "B", "Zzz"], fichas)
    assert p["desconocidos"] == ["B", "Zzz"]  # en el orden recibido
    assert p["n_conocidos"] == 1
    assert p["prop_magico"] == pytest.approx(1.0)
    assert p["prop_fisico"] == pytest.approx(0.0)
    assert p["enganche_total"] == 3


def test_enganche_y_control_suman_y_vacio_vale_cero():
    fichas = {
        "A": ficha(enganche=3, control=1),
        "B": ficha(enganche=2, control=""),
        "C": ficha(enganche="", control=2),
    }
    p = composicion.perfil_equipo(["A", "B", "C"], fichas)
    assert p["enganche_total"] == 5
    assert p["control_total"] == 3


@pytest.mark.parametrize(
    "escalas, esperado",
    [
        (["tardio", "tardio", "medio"], "tardio"),
        (["temprano", "tardio"], "temprano"),  # empate: gana el orden temprano, medio, tardio
        (["medio", "tardio"], "medio"),
        (["", ""], ""),
    ],
)
def test_escala_dominante(escalas, esperado):
    fichas = {str(i): ficha(escala=e) for i, e in enumerate(escalas)}
    assert composicion.perfil_equipo(list(fichas), fichas)["escala_dominante"] == esperado


def test_arquetipos_unicos_ordenados_y_cuerpo_a_cuerpo():
    fichas = {
        "A": ficha(arquetipo="tanque", alcance="cuerpo"),
        "B": ficha(arquetipo="asesino", alcance="cuerpo"),
        "C": ficha(arquetipo="tanque", alcance="distancia"),
        "D": ficha(arquetipo="", alcance="distancia"),
    }
    p = composicion.perfil_equipo(["A", "B", "C", "D"], fichas)
    assert p["arquetipos"] == ["asesino", "tanque"]  # sin repetir, sin vacíos, ordenados
    assert p["n_cuerpo"] == 2


def test_perfil_no_modifica_sus_argumentos():
    fichas = {"A": ficha()}
    campeones = ["A", "Zzz"]
    composicion.perfil_equipo(campeones, fichas)
    assert campeones == ["A", "Zzz"]
    assert fichas == {"A": ficha()}


def _perfil(fichas_por_campeon: dict) -> dict:
    return composicion.perfil_equipo(list(fichas_por_campeon), fichas_por_campeon)


def test_contraste_claves_y_diferencias():
    aliado = _perfil({"A": ficha(enganche=3, control=1, escala="tardio"), "B": ficha(enganche=1, control=1, escala="tardio")})
    enemigo = _perfil({"C": ficha(enganche=1, control=3, escala="temprano")})
    c = composicion.contraste(aliado, enemigo)
    assert set(c) == CLAVES_CONTRASTE
    assert c["dif_enganche"] == 3  # 4 - 1
    assert c["dif_control"] == -1  # 2 - 3
    assert c["mas_enganche"] == "aliado"
    assert c["mas_control"] == "enemigo"
    assert c["mejor_escala"] == "aliado"  # tardio > temprano


def test_contraste_igual_cuando_empatan_o_no_se_sabe():
    a = _perfil({"A": ficha(enganche=2, control=2, escala="medio")})
    b = _perfil({"B": ficha(enganche=2, control=2, escala="medio")})
    c = composicion.contraste(a, b)
    assert (c["mas_enganche"], c["mas_control"], c["mejor_escala"]) == ("igual", "igual", "igual")
    sin_datos = composicion.perfil_equipo([], {})
    assert composicion.contraste(a, sin_datos)["mejor_escala"] == "igual"  # falta un lado


def test_enemigo_casi_todo_un_tipo_de_dano_desde_70_por_ciento():
    siete_fisico = {f"f{i}": ficha(dano="fisico") for i in range(7)} | {f"m{i}": ficha(dano="magico") for i in range(3)}
    seis_fisico = {f"f{i}": ficha(dano="fisico") for i in range(6)} | {f"m{i}": ficha(dano="magico") for i in range(4)}
    siete_magico = {f"f{i}": ficha(dano="fisico") for i in range(3)} | {f"m{i}": ficha(dano="magico") for i in range(7)}
    mi_equipo = _perfil({"A": ficha()})

    c = composicion.contraste(mi_equipo, _perfil(siete_fisico))
    assert (c["enemigo_casi_todo_fisico"], c["enemigo_casi_todo_magico"], c["enemigo_un_tipo_dano"]) == (True, False, True)
    c = composicion.contraste(mi_equipo, _perfil(seis_fisico))
    assert (c["enemigo_casi_todo_fisico"], c["enemigo_casi_todo_magico"], c["enemigo_un_tipo_dano"]) == (False, False, False)
    c = composicion.contraste(mi_equipo, _perfil(siete_magico))
    assert (c["enemigo_casi_todo_fisico"], c["enemigo_casi_todo_magico"], c["enemigo_un_tipo_dano"]) == (False, True, True)


def test_enemigo_sin_datos_no_cuenta_como_un_solo_tipo_de_dano():
    c = composicion.contraste(composicion.perfil_equipo([], {}), composicion.perfil_equipo([], {}))
    assert c["enemigo_un_tipo_dano"] is False


def test_construir_contexto_tiene_las_tres_partes():
    fichas = {"A": ficha(dano="magico"), "B": ficha(dano="fisico")}
    ctx = composicion.construir_contexto(["A"], ["B", "Zzz"], fichas)
    assert set(ctx) == {"aliado", "enemigo", "contraste"}
    assert set(ctx["aliado"]) == CLAVES_PERFIL
    assert ctx["enemigo"]["desconocidos"] == ["Zzz"]
    assert set(ctx["contraste"]) == CLAVES_CONTRASTE
    assert ctx["aliado"]["prop_magico"] == pytest.approx(1.0)
    assert ctx["enemigo"]["prop_fisico"] == pytest.approx(1.0)
