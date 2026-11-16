"""Datos estáticos oficiales (Data Dragon): campeones, ítems, runas y hechizos."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import httpx

BASE = "https://ddragon.leagueoflegends.com"
ARCHIVOS = ("champion", "item", "runesReforged", "summoner")


def ultima_version(http: httpx.Client) -> str:
    r = http.get(f"{BASE}/api/versions.json")
    r.raise_for_status()
    return r.json()[0]


def descargar(
    static_dir: Path,
    locale: str = "es_MX",
    version: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, dict[str, object]]:
    """Descarga los archivos de la versión indicada (o la última) y los guarda en disco."""
    with httpx.Client(timeout=30.0, transport=transport) as http:
        version = version or ultima_version(http)
        destino = static_dir / version
        destino.mkdir(parents=True, exist_ok=True)
        datos: dict[str, object] = {}
        for nombre in ARCHIVOS:
            r = http.get(f"{BASE}/cdn/{version}/data/{locale}/{nombre}.json")
            r.raise_for_status()
            datos[nombre] = r.json()
            (destino / f"{nombre}.json").write_text(
                json.dumps(datos[nombre], ensure_ascii=False), encoding="utf-8"
            )
    return version, datos


def cargar_en_db(con: duckdb.DuckDBPyConnection, version: str, datos: dict[str, object]) -> dict[str, int]:
    campeones = [
        (int(c["key"]), c["id"], c["name"], ",".join(c.get("tags", [])), version)
        for c in datos["champion"]["data"].values()  # type: ignore[index]
    ]
    items = [
        (
            int(item_id),
            it.get("name"),
            (it.get("gold") or {}).get("total"),
            ",".join(it.get("tags", [])),
            version,
        )
        for item_id, it in datos["item"]["data"].items()  # type: ignore[index]
    ]
    con.executemany("INSERT OR REPLACE INTO campeones VALUES (?, ?, ?, ?, ?)", campeones)
    con.executemany("INSERT OR REPLACE INTO items VALUES (?, ?, ?, ?, ?)", items)
    return {"campeones": len(campeones), "items": len(items)}
