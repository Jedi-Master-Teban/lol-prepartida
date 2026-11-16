"""Configuración leída de variables de entorno y de un archivo .env opcional."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def cargar_env(ruta: Path) -> None:
    """Carga pares CLAVE=valor de un .env sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    api_key: str
    game_name: str
    tag_line: str
    platform: str
    region: str
    locale: str
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "prepartida.duckdb"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "crudo"

    @property
    def static_dir(self) -> Path:
        return self.data_dir / "estaticos"


def leer_config(env_file: Path | None = None) -> Config:
    cargar_env(env_file or Path(".env"))
    return Config(
        api_key=os.environ.get("RIOT_API_KEY", ""),
        game_name=os.environ.get("RIOT_GAME_NAME", ""),
        tag_line=os.environ.get("RIOT_TAG_LINE", ""),
        platform=os.environ.get("RIOT_PLATFORM", "la1"),
        region=os.environ.get("RIOT_REGION", "americas"),
        locale=os.environ.get("DDRAGON_LOCALE", "es_MX"),
        data_dir=Path(os.environ.get("PREPARTIDA_DATA_DIR", "data")),
    )
