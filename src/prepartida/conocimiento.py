"""Fichas automáticas de campeones, calculadas solo de Data Dragon."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ORDEN_BASE = [
    "dano",
    "alcance",
    "etiquetas_riot",
    "enganche",
    "control",
    "escala",
    "arquetipo",
    "verificado",
    "fuente",
]

_CAMPOS_CURADOS = {"enganche", "control", "escala", "arquetipo", "verificado", "fuente"}
_NOMBRE_SECCION = re.compile(r"^[A-Za-z0-9_-]+$")
COMENTARIO = "# Fichas de campeones. `dano` es una aproximación (info.attack frente a info.magic de Data Dragon)."


def clasificar_dano(ataque: int, magia: int) -> str:
    """Devuelve "magico", "fisico" o "mixto" segun info.attack e info.magic."""
    if magia >= ataque + 3:
        return "magico"
    if ataque >= magia + 3:
        return "fisico"
    return "mixto"


def clasificar_alcance(rango_ataque: float) -> str:
    """Devuelve "cuerpo" si el alcance es <= 300, si no "distancia"."""
    if rango_ataque <= 300:
        return "cuerpo"
    return "distancia"


def generar_fichas(champion_json: dict, existentes: dict | None = None) -> dict[str, dict]:
    """Calcula una ficha por campeón de champion_json, conservando lo curado de existentes."""
    if existentes is None:
        existentes = {}
    data = champion_json["data"]
    fichas: dict[str, dict] = {}
    for id_, campeon in data.items():
        info = campeon["info"]
        stats = campeon["stats"]
        if id_ in existentes:
            base = dict(existentes[id_])
            ficha: dict = {}
            ficha["dano"] = clasificar_dano(info["attack"], info["magic"])
            ficha["alcance"] = clasificar_alcance(stats["attackrange"])
            ficha["etiquetas_riot"] = list(campeon.get("tags", []))
            for campo in _CAMPOS_CURADOS:
                if campo in base:
                    ficha[campo] = base[campo]
        else:
            ficha = {
                "dano": clasificar_dano(info["attack"], info["magic"]),
                "alcance": clasificar_alcance(stats["attackrange"]),
                "etiquetas_riot": list(campeon.get("tags", [])),
                "enganche": "",
                "control": "",
                "escala": "",
                "arquetipo": "",
                "verificado": False,
            }
        fichas[id_] = ficha
    for id_, ficha in existentes.items():
        if id_ not in data:
            fichas[id_] = dict(ficha)
    return fichas


def leer_fichas(ruta: Path) -> dict[str, dict]:
    """Lee las fichas con tomllib; si no existe el archivo devuelve {}."""
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    with ruta.open("rb") as f:
        return tomllib.load(f)


def _valor_toml(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return str(valor)
    return json.dumps(valor, ensure_ascii=False)


def _seccion(nombre: str) -> str:
    if _NOMBRE_SECCION.fullmatch(nombre):
        return nombre
    return json.dumps(nombre, ensure_ascii=False)


def _orden_campos(ficha: dict) -> list[str]:
    base = [c for c in ORDEN_BASE if c in ficha]
    otros = sorted(c for c in ficha if c not in ORDEN_BASE)
    return base + otros


def escribir_fichas(fichas: dict[str, dict], ruta: Path) -> None:
    """Escribe las fichas en TOML, ordenadas alfabeticamente, de forma estable byte a byte."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [COMENTARIO]
    for nombre in sorted(fichas):
        lineas.append("")
        lineas.append(f"[{_seccion(nombre)}]")
        for campo in _orden_campos(fichas[nombre]):
            lineas.append(f"{campo} = {_valor_toml(fichas[nombre][campo])}")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def version_mas_reciente(static_dir: Path) -> str:
    """Devuelve la version mas reciente (comparando numeros) que tenga champion.json."""
    static_dir = Path(static_dir)
    if not static_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de estaticos: {static_dir}")
    versiones = [
        sub.name
        for sub in static_dir.iterdir()
        if sub.is_dir() and (sub / "champion.json").exists()
    ]
    if not versiones:
        raise FileNotFoundError(f"No hay datos de campeones en {static_dir}")
    return max(versiones, key=lambda v: tuple(int(x) for x in v.split(".")))
