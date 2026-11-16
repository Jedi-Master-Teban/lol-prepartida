"""Línea de comandos: prepartida <comando>."""

from __future__ import annotations

import argparse
import sys

from prepartida import db, ddragon, estado, ingest
from prepartida.config import leer_config
from prepartida.riot_client import RiotClient, RiotError


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

    sub.add_parser("app", help="Abre la app web local").set_defaults(func=_cmd_app)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RiotError as e:
        print(f"Error de la API de Riot: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
