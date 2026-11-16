"""Perfil del jugador (pool, roles y metas) leído de perfil.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Perfil:
    pool: tuple[str, ...] = ()
    rol_principal: str = "MIDDLE"
    rol_secundario: str = "BOTTOM"
    meta_cs_10: int = 70
    meta_muertes_14: int = 1
    partidas_por_sesion: int = 3
    desfase_horas: int = 10
    extra: dict = field(default_factory=dict)


def leer_perfil(ruta: Path | str = "perfil.toml") -> Perfil:
    ruta = Path(ruta)
    if not ruta.exists():
        return Perfil()
    datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    roles = datos.get("roles", {})
    metas = datos.get("metas", {})
    sesion = datos.get("sesion", {})
    return Perfil(
        pool=tuple(datos.get("pool", [])),
        rol_principal=roles.get("principal", "MIDDLE"),
        rol_secundario=roles.get("secundario", "BOTTOM"),
        meta_cs_10=metas.get("cs_10", 70),
        meta_muertes_14=metas.get("muertes_antes_de_14", 1),
        partidas_por_sesion=metas.get("partidas_por_sesion", 3),
        desfase_horas=sesion.get("desfase_horas", 10),
    )
