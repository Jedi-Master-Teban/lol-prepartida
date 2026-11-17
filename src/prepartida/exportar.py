"""Exporta los datos del jugador a los seis JSON del contrato (`docs/data/`).

El contrato está en `PLAN.md`, sección 3. Los archivos son públicos: no pueden
contener identificadores de otros jugadores ni el PUUID del propio jugador.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from prepartida import metricas
from prepartida.perfil import Perfil

MAX_MINUTO = 40
ORO_ITEM_COMPLETO = 2200
COLA_SOLO_DUO = "RANKED_SOLO_5x5"


def exportar(
    con: duckdb.DuckDBPyConnection,
    perfil: Perfil,
    static_dir: Path,
    destino: Path,
) -> dict[str, int]:
    """Escribe los seis JSON del contrato en `destino`. Devuelve el conteo de elementos por archivo."""
    jugador = con.execute(
        "SELECT puuid, game_name, tag_line FROM jugador ORDER BY actualizado DESC LIMIT 1"
    ).fetchone()
    if jugador is None:
        raise ValueError("No hay jugador en la base")
    puuid, game_name, tag_line = jugador

    version = _version_ddragon(con, static_dir)
    if version is None:
        raise ValueError("No hay versión de Data Dragon: ejecuta `prepartida estaticos`")
    df = metricas.partidas_del_jugador(con, puuid, perfil)

    meta = _meta(con, puuid, perfil, game_name, tag_line, version)
    partidas = _partidas(df)
    curvas = _curvas(con, puuid, list(df["match_id"]))
    muertes = _muertes(con, puuid)
    compras = _compras(con, puuid)
    estaticos = _estaticos(con, df, static_dir, version, compras)

    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    _escribir(destino, "meta.json", meta)
    _escribir(destino, "partidas.json", partidas)
    _escribir(destino, "curvas.json", curvas)
    _escribir(destino, "muertes.json", muertes)
    _escribir(destino, "compras.json", compras)
    _escribir(destino, "estaticos.json", estaticos)

    return {
        "meta": 1,
        "partidas": len(partidas),
        "curvas": len(curvas),
        "muertes": len(muertes),
        "compras": sum(len(v) for v in compras.values()),
        "estaticos": sum(len(v) for v in estaticos.values()),
    }


def _meta(
    con: duckdb.DuckDBPyConnection,
    puuid: str,
    perfil: Perfil,
    game_name: str,
    tag_line: str,
    version: str | None,
) -> dict[str, Any]:
    """Datos del jugador, su rango y el perfil de preparation."""
    rango = con.execute(
        "SELECT tier, division, lp, victorias, derrotas FROM rango_historial "
        "WHERE puuid = ? AND cola = ? ORDER BY tomado DESC LIMIT 1",
        [puuid, COLA_SOLO_DUO],
    ).fetchone()
    tier, division, lp, victorias, derrotas = rango if rango else (None, None, None, None, None)
    return {
        "generado": _iso_utc(datetime.now(timezone.utc)),
        "version_ddragon": version,
        "jugador": {
            "game_name": game_name,
            "tag_line": tag_line,
            "tier": tier,
            "division": division,
            "lp": lp,
            "victorias": victorias,
            "derrotas": derrotas,
        },
        "perfil": {
            "pool": list(perfil.pool),
            "rol_principal": perfil.rol_principal,
            "rol_secundario": perfil.rol_secundario,
            "meta_cs_10": perfil.meta_cs_10,
            "meta_muertes_14": perfil.meta_muertes_14,
            "partidas_por_sesion": perfil.partidas_por_sesion,
            "desfase_horas": perfil.desfase_horas,
        },
    }


def _partidas(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Una entrada por partida, con los campos del contrato en la sección 3.2."""
    salida = []
    for fila in df.to_dict("records"):
        salida.append(
            {
                "match_id": fila["match_id"],
                "inicio": _iso_utc(fila["inicio"]),
                "dia_sesion": str(fila["dia_sesion"]),
                "n_del_dia": int(fila["n_del_dia"]),
                "parche": fila["parche"],
                "champion_id": _entero(fila.get("champion_id")),
                "campeon": fila["campeon"],
                "posicion": fila["posicion"] or "",
                "lado": fila["lado"],
                "victoria": bool(fila["victoria"]),
                "asesinatos": int(fila["asesinatos"]),
                "muertes": int(fila["muertes"]),
                "asistencias": int(fila["asistencias"]),
                "duracion_min": _redondear(fila["duracion_min"], 1),
                "cs_min": _redondear(fila["cs_min"], 1),
                "rival_champion_id": _entero(fila.get("rival_champion_id")),
                "rival": fila.get("rival"),
                "cs_10": _redondear(fila.get("cs_10"), 1),
                "dif_oro_10": _redondear(fila.get("dif_oro_10"), 0),
                "dif_oro_15": _redondear(fila.get("dif_oro_15"), 0),
                "muertes_14": int(fila["muertes_14"]),
                "primera_muerte_min": _redondear(fila.get("primera_muerte_min"), 1),
                "en_pool": bool(fila["en_pool"]),
                "items": [int(i) for i in _items(fila)],
                "hechizos": [_entero(fila.get("hechizo1")), _entero(fila.get("hechizo2"))],
                "runa_clave": _entero(fila.get("runa_clave")),
                "arbol_primario": _entero(fila.get("arbol_primario")),
                "arbol_secundario": _entero(fila.get("arbol_secundario")),
            }
        )
    return salida


def _curvas(
    con: duckdb.DuckDBPyConnection, puuid: str, match_ids: list[str]
) -> dict[str, dict[str, list[Any]]]:
    """Oro, CS y diferencia de oro por minuto de cada partida."""
    yo, rival = _participantes(con, puuid)
    cuadros = _cuadros(con, puuid)
    salida: dict[str, dict[str, list[Any]]] = {}
    for match_id in match_ids:
        frames = cuadros.get((match_id, yo.get(match_id)), {})
        frames_rival = cuadros.get((match_id, rival.get(match_id)), {})
        minutos = sorted(m for m in frames if m <= MAX_MINUTO)
        largo = (minutos[-1] + 1) if minutos else 0
        oro = [frames[m][0] if m in frames else None for m in range(largo)]
        cs = [frames[m][1] if m in frames else None for m in range(largo)]
        dif_oro = []
        for m in range(largo):
            mio = frames.get(m)
            suyo = frames_rival.get(m)
            dif_oro.append(mio[0] - suyo[0] if mio and suyo else None)
        salida[match_id] = {"oro": oro, "cs": cs, "dif_oro": dif_oro}
    return salida


def _muertes(con: duckdb.DuckDBPyConnection, puuid: str) -> list[dict[str, Any]]:
    """Cada muerte del jugador con su posición en el mapa."""
    filas = con.execute(
        "SELECT e.match_id, e.ts_ms, "
        "       CAST(json_extract(e.detalle, '$.position.x') AS DOUBLE) AS x, "
        "       CAST(json_extract(e.detalle, '$.position.y') AS DOUBLE) AS y "
        "FROM eventos e "
        "JOIN participantes p ON p.match_id = e.match_id AND p.puuid = ? "
        "WHERE e.tipo = 'CHAMPION_KILL' "
        "  AND CAST(json_extract(e.detalle, '$.victimId') AS INTEGER) = p.participant_id "
        "ORDER BY e.match_id, e.ts_ms",
        [puuid],
    ).fetchall()
    salida = []
    for match_id, ts_ms, x, y in filas:
        if x is None or y is None:
            continue
        salida.append(
            {
                "match_id": match_id,
                "minuto": round(ts_ms / 60000.0, 1),
                "x": int(x),
                "y": int(y),
            }
        )
    return salida


def _compras(con: duckdb.DuckDBPyConnection, puuid: str) -> dict[str, list[dict[str, Any]]]:
    """Compras del jugador agrupadas por partida, solo de ítems completos."""
    filas = con.execute(
        "SELECT e.match_id, e.ts_ms, "
        "       CAST(json_extract(e.detalle, '$.itemId') AS INTEGER) AS item_id "
        "FROM eventos e "
        "JOIN participantes p ON p.match_id = e.match_id AND p.puuid = ? "
        "WHERE e.tipo = 'ITEM_PURCHASED' "
        "  AND CAST(json_extract(e.detalle, '$.participantId') AS INTEGER) = p.participant_id "
        "ORDER BY e.match_id, e.ts_ms",
        [puuid],
    ).fetchall()
    oro = {
        item_id: total
        for item_id, total in con.execute("SELECT item_id, oro_total FROM items").fetchall()
    }
    salida: dict[str, list[dict[str, Any]]] = {}
    for match_id, ts_ms, item_id in filas:
        total = oro.get(item_id)
        if item_id is None or total is None or total < ORO_ITEM_COMPLETO:
            continue
        salida.setdefault(match_id, []).append(
            {"minuto": round(ts_ms / 60000.0, 1), "item_id": int(item_id)}
        )
    return salida


def _estaticos(
    con: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
    static_dir: Path,
    version: str | None,
    compras: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Solo los elementos referenciados por el resto de los archivos."""
    camp_ids: set[int] = set()
    item_ids: set[int] = set()
    runa_ids: set[int] = set()
    arbol_ids: set[int] = set()
    hechizo_ids: set[int] = set()
    for fila in df.to_dict("records"):
        for valor in (fila.get("champion_id"), fila.get("rival_champion_id")):
            if valor is not None:
                camp_ids.add(int(valor))
        for item in _items(fila):
            item_ids.add(int(item))
        for valor in (fila.get("runa_clave"),):
            if valor is not None:
                runa_ids.add(int(valor))
        for valor in (fila.get("arbol_primario"), fila.get("arbol_secundario")):
            if valor is not None:
                arbol_ids.add(int(valor))
        for valor in (fila.get("hechizo1"), fila.get("hechizo2")):
            if valor is not None:
                hechizo_ids.add(int(valor))
    for lista in compras.values():
        for compra in lista:
            item_ids.add(int(compra["item_id"]))
        for valor in (fila.get("runa_clave"),):
            if valor is not None:
                runa_ids.add(int(valor))
        for valor in (fila.get("arbol_primario"), fila.get("arbol_secundario")):
            if valor is not None:
                arbol_ids.add(int(valor))
        for valor in (fila.get("hechizo1"), fila.get("hechizo2")):
            if valor is not None:
                hechizo_ids.add(int(valor))

    versioning = Path(static_dir) / str(version)
    runas, arboles = _runas(versioning, runa_ids, arbol_ids)
    hechizos = _hechizos(versioning, hechizo_ids)

    return {
        "campeones": {
            str(cid): {"clave": clave, "nombre": nombre}
            for cid, clave, nombre in _consulta(con, "campeones", camp_ids)
        },
        "items": {
            str(iid): {"nombre": nombre} for iid, nombre in _consulta(con, "items", item_ids)
        },
        "runas": runas,
        "arboles": arboles,
        "hechizos": hechizos,
    }


def _consulta(con: duckdb.DuckDBPyConnection, tabla: str, ids: set[int]) -> list[tuple]:
    """Filas de `campeones` o `items` para los identificadores dados."""
    if not ids:
        return []
    marcas = ", ".join("?" for _ in ids)
    columna = "champion_id" if tabla == "campeones" else "item_id"
    nombre = "clave, nombre" if tabla == "campeones" else "nombre"
    return con.execute(
        f"SELECT {columna}, {nombre} FROM {tabla} WHERE {columna} IN ({marcas}) ORDER BY {columna}",
        sorted(ids),
    ).fetchall()


def _runas(carpeta: Path, runa_ids: set[int], arbol_ids: set[int]) -> tuple[dict, dict]:
    """Runas y árboles de runas referenciados, con nombre e icono."""
    ruta = carpeta / "runesReforged.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    runas: dict[str, dict[str, Any]] = {}
    arboles: dict[str, dict[str, Any]] = {}
    for arbol in datos:
        if str(arbol.get("id")) in {str(i) for i in arbol_ids}:
            arboles[str(arbol["id"])] = {"nombre": arbol["name"], "icono": arbol["icon"]}
        for slot in arbol.get("slots") or []:
            for runa in slot.get("runes") or []:
                if str(runa.get("id")) in {str(i) for i in runa_ids}:
                    runas[str(runa["id"])] = {"nombre": runa["name"], "icono": runa["icon"]}
    return runas, arboles


def _hechizos(carpeta: Path, hechizo_ids: set[int]) -> dict[str, dict[str, Any]]:
    """Hechizos referenciados, con su clave y su nombre."""
    ruta = carpeta / "summoner.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    pedidos = {str(i) for i in hechizo_ids}
    salida: dict[str, dict[str, Any]] = {}
    for hechizo in (datos.get("data") or {}).values():
        key = str(hechizo.get("key"))
        if key in pedidos:
            salida[key] = {"clave": hechizo.get("id"), "nombre": hechizo.get("name")}
    return salida


def _participantes(con: duckdb.DuckDBPyConnection, puuid: str) -> tuple[dict[str, int], dict[str, int | None]]:
    """Participant id del jugador y del rival de posición, por partida."""
    filas = con.execute(
        "SELECT p.match_id, p.participant_id, r.participant_id "
        "FROM participantes p "
        "LEFT JOIN participantes r "
        "  ON r.match_id = p.match_id AND r.posicion = p.posicion AND r.lado <> p.lado "
        " AND p.posicion <> '' "
        "WHERE p.puuid = ?",
        [puuid],
    ).fetchall()
    yo: dict[str, int] = {}
    rival: dict[str, int | None] = {}
    for match_id, pid, rpid in filas:
        yo.setdefault(match_id, pid)
        rival.setdefault(match_id, rpid)
    return yo, rival


def _cuadros(
    con: duckdb.DuckDBPyConnection, puuid: str
) -> dict[tuple[str, int], dict[int, tuple[int, int]]]:
    """Oro y CS de cada participante y minuto, para las partidas del jugador."""
    filas = con.execute(
        "SELECT c.match_id, c.participant_id, c.minuto, c.oro_total, c.cs, c.cs_jungla "
        "FROM cuadros c "
        "WHERE c.match_id IN (SELECT match_id FROM participantes WHERE puuid = ?)",
        [puuid],
    ).fetchall()
    datos: dict[tuple[str, int], dict[int, tuple[int, int]]] = {}
    for match_id, pid, minuto, oro, cs, cs_jungla in filas:
        clave = (match_id, pid)
        minutos = datos.setdefault(clave, {})
        minutos[minuto] = (int(oro or 0), int(cs or 0) + int(cs_jungla or 0))
    return datos


def _items(fila: dict[str, Any]) -> list[int]:
    """Los seis o siete ítems comprados en la partida, sin ceros."""
    items = []
    for i in range(7):
        valor = fila.get(f"item{i}")
        if valor:
            items.append(int(valor))
    return items


def _version_ddragon(con: duckdb.DuckDBPyConnection, static_dir: Path) -> str | None:
    """La versión de Data Dragon más reciente de la base (o la carpeta más nueva)."""
    versiones = [
        v
        for (v,) in con.execute(
            "SELECT DISTINCT version FROM campeones WHERE version IS NOT NULL"
        ).fetchall()
    ]
    if versiones:
        return max(versiones, key=_clave_version)
    carpetas = [p.name for p in Path(static_dir).glob("*") if p.is_dir()]
    return max(carpetas, key=_clave_version) if carpetas else None


def _clave_version(version: str) -> tuple[int, ...]:
    """'16.22.1' -> (16, 22, 1), para comparar versiones como números."""
    partes = []
    for trozo in version.split("."):
        partes.append(int(trozo) if trozo.isdigit() else 0)
    return tuple(partes)


def _escribir(destino: Path, nombre: str, datos: Any) -> None:
    """Escribe un JSON del contrato en UTF-8, sin NaN y con `null` para lo que falta."""
    texto = json.dumps(_limpio(datos), ensure_ascii=False, indent=2, allow_nan=False)
    (destino / nombre).write_text(texto + "\n", encoding="utf-8")


def _limpio(valor: Any) -> Any:
    """Convierte NaN, NaT y tipos de numpy/pandas en valores válidos de JSON."""
    if valor is None or valor is pd.NaT:
        return None
    if isinstance(valor, (bool, int, str)):
        return valor
    if isinstance(valor, float):
        return None if not math.isfinite(valor) else valor
    if isinstance(valor, dict):
        return {str(clave): _limpio(item) for clave, item in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [_limpio(item) for item in valor]
    if isinstance(valor, pd.Timestamp):
        return _iso_utc(valor.to_pydatetime())
    if isinstance(valor, datetime):
        return _iso_utc(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    if hasattr(valor, "item"):
        try:
            return _limpio(valor.item())
        except (AttributeError, ValueError):
            return None
    try:
        if bool(pd.isna(valor)):
            return None
    except (TypeError, ValueError):
        pass
    return valor


def _iso_utc(momento: datetime) -> str:
    """'2026-11-15T23:10:00Z' a partir de un momento en UTC."""
    if isinstance(momento, pd.Timestamp):
        momento = momento.to_pydatetime()
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redondear(valor: Any, decimales: int) -> int | float | None:
    """Redondea un número; `None` si falta."""
    if valor is None:
        return None
    try:
        if bool(pd.isna(valor)):
            return None
    except (TypeError, ValueError):
        pass
    numero = float(valor)
    if decimales == 0:
        return int(round(numero))
    return round(numero, decimales)


def _entero(valor: Any) -> int | None:
    """Un entero o `None` si falta."""
    if valor is None:
        return None
    try:
        if bool(pd.isna(valor)):
            return None
    except (TypeError, ValueError):
        pass
    return int(valor)
