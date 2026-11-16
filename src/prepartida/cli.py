"""Línea de comandos: prepartida <comando>."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import duckdb

from prepartida import db, ddragon, estado, exportar, ingest
from prepartida.config import leer_config
from prepartida.perfil import leer_perfil
from prepartida.riot_client import ClaveInvalida, RiotClient, RiotError


def _cmd_init(_args: argparse.Namespace) -> int:
    cfg = leer_config()
    db.conectar(cfg.db_path).close()
    print(f"Base creada en {cfg.db_path}")
    return 0


def _cmd_estaticos(args: argparse.Namespace) -> int:
    cfg = leer_config()
    version, datos = ddragon.descargar(cfg.static_dir, cfg.locale, args.version)
    con = db.conectar(cfg.db_path)
    conteo = ddragon.cargar_en_db(con, version, datos)
    con.close()
    print(f"Data Dragon {version}: {conteo['campeones']} campeones, {conteo['items']} ítems")
    return 0


def _cmd_ingesta(args: argparse.Namespace) -> int:
    cfg = leer_config()
    if not cfg.game_name or not cfg.tag_line:
        print("Faltan RIOT_GAME_NAME y RIOT_TAG_LINE en .env", file=sys.stderr)
        return 2
    client = RiotClient(cfg.api_key, cfg.platform, cfg.region)
    con = db.conectar(cfg.db_path)
    try:
        puuid = ingest.ingerir_perfil(client, con, cfg.game_name, cfg.tag_line)
        print(f"Perfil actualizado: {cfg.game_name} #{cfg.tag_line}")
        resumen = ingest.ingerir_historial(
            client,
            con,
            puuid,
            max_partidas=args.max,
            queue=None if args.todas_las_colas else 420,
            raw_dir=cfg.raw_dir,
            aviso=print,
        )
        print(
            f"Listo: {resumen['nuevas']} partidas nuevas "
            f"({resumen['sin_linea_de_tiempo']} sin línea de tiempo)"
        )
    finally:
        con.close()
        client.close()
    return 0


def _cmd_estado(_args: argparse.Namespace) -> int:
    cfg = leer_config()
    con = db.conectar(cfg.db_path)
    print(estado.texto(con))
    con.close()
    return 0


def _cmd_app(_args: argparse.Namespace) -> int:
    import subprocess
    from pathlib import Path

    ruta = Path(__file__).with_name("app.py")
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(ruta)])


def _abrir_lectura(ruta: Path) -> duckdb.DuckDBPyConnection:
    """Abre la base en solo lectura: exportar no modifica los datos."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe la base {ruta}. Ejecuta primero: prepartida ingesta")
    return duckdb.connect(str(ruta), read_only=True)


def _cmd_exportar(args: argparse.Namespace) -> int:
    cfg = leer_config()
    try:
        con = _abrir_lectura(cfg.db_path)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    destino = Path(args.destino).resolve()
    try:
        perfil = leer_perfil(args.perfil)
        conteo = exportar.exportar(con, perfil, cfg.static_dir, destino)
    finally:
        con.close()
    print(f"Datos escritos en {destino}")
    for nombre, n in conteo.items():
        print(f"  {nombre}: {n}")
    return 0


def _cmd_publicar(args: argparse.Namespace) -> int:
    """Ingesta, exporta y publica los datos en git."""
    try:
        codigo = _cmd_ingesta(args)
    except ClaveInvalida as e:
        print(f"La ingesta falló: {e}", file=sys.stderr)
        return 1
    if codigo != 0:
        return codigo
    codigo = _cmd_exportar(args)
    if codigo != 0:
        return codigo
    return _publicar_en_git(Path(args.destino).resolve())


def _publicar_en_git(destino: Path) -> int:
    """Agrega los datos al repositorio y los sube, si hay cambios."""
    raiz = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if raiz.returncode != 0:
        print("No estás dentro de un repositorio git.", file=sys.stderr)
        return 1
    raiz = Path(raiz.stdout.strip())

    agregar = subprocess.run(
        ["git", "add", str(destino)], cwd=raiz, capture_output=True, text=True
    )
    if agregar.returncode != 0:
        print(f"No se pudieron agregar los datos: {agregar.stderr.strip()}", file=sys.stderr)
        return 1

    estado = subprocess.run(
        ["git", "status", "--porcelain", "--", str(destino)],
        cwd=raiz,
        capture_output=True,
        text=True,
    )
    if not estado.stdout.strip():
        print("Los datos no cambiaron: no hay nada que publicar.")
        return 0

    mensaje = f"datos: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    commit = subprocess.run(
        ["git", "commit", "-m", mensaje], cwd=raiz, capture_output=True, text=True
    )
    if commit.returncode != 0:
        print(f"No se pudo hacer el commit: {commit.stderr.strip()}", file=sys.stderr)
        return 1
    print(f"Commit: {mensaje}")

    remotos = subprocess.run(
        ["git", "remote"], cwd=raiz, capture_output=True, text=True
    ).stdout.strip()
    if not remotos:
        print("No hay remoto configurado: se omite el push.")
        return 0

    push = subprocess.run(["git", "push"], cwd=raiz, capture_output=True, text=True)
    if push.returncode != 0:
        print(f"No se pudo hacer push: {push.stderr.strip()}", file=sys.stderr)
        return 1
    print("Datos publicados.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prepartida", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("init", help="Crea la base local").set_defaults(func=_cmd_init)

    p = sub.add_parser("estaticos", help="Descarga campeones, ítems, runas y hechizos")
    p.add_argument("--version", help="Versión de Data Dragon (por defecto, la última)")
    p.set_defaults(func=_cmd_estaticos)

    p = sub.add_parser("ingesta", help="Descarga tu perfil y tu historial de partidas")
    p.add_argument("--max", type=int, default=200, help="Máximo de partidas a revisar")
    p.add_argument(
        "--todas-las-colas", action="store_true", help="Incluye colas distintas de Solo/Dúo"
    )
    p.set_defaults(func=_cmd_ingesta)

    sub.add_parser("estado", help="Muestra tu rango y tu rendimiento por campeón").set_defaults(
        func=_cmd_estado
    )

    p = sub.add_parser("exportar", help="Escribe los datos de la página en docs/data")
    p.add_argument("--destino", default="docs/data", help="Carpeta de destino (docs/data)")
    p.add_argument("--perfil", default="perfil.toml", help="Archivo de perfil (perfil.toml)")
    p.set_defaults(func=_cmd_exportar)

    p = sub.add_parser("publicar", help="Ingesta, exporta y sube los datos a git")
    p.add_argument("--destino", default="docs/data", help="Carpeta de destino (docs/data)")
    p.add_argument("--perfil", default="perfil.toml", help="Archivo de perfil (perfil.toml)")
    p.add_argument("--max", type=int, default=200, help="Máximo de partidas a revisar")
    p.add_argument(
        "--todas-las-colas", action="store_true", help="Incluye colas distintas de Solo/Dúo"
    )
    p.set_defaults(func=_cmd_publicar)

    sub.add_parser("app", help="Abre la app web local").set_defaults(func=_cmd_app)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RiotError as e:
        print(f"Error de la API de Riot: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
