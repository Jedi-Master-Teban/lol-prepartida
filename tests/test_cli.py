from __future__ import annotations

import json
import subprocess

import httpx
import pytest

from prepartida import cli, db, ingest
from prepartida.riot_client import RateLimiter, RiotClient

VERSION = "16.22.1"
RUNAS = [
    {
        "id": 8100,
        "name": "Dominación",
        "icon": "perk-images/Styles/7200_Domination.png",
        "slots": [{"runes": [{"id": 8112, "name": "Electrocutar", "icon": "icono.png"}]}],
    }
]
HECHIZOS = {
    "data": {
        "SummonerFlash": {"id": "SummonerFlash", "name": "Destello", "key": "4"},
        "SummonerDot": {"id": "SummonerDot", "name": "Ignición", "key": "14"},
    }
}


def _base(api, ruta):
    con = db.conectar(ruta / "prepartida.duckdb")
    cliente = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    puuid = ingest.ingerir_perfil(cliente, con, "SithLordDropout", "LAN")
    ingest.ingerir_historial(cliente, con, puuid)
    con.close()


def _estaticos_falsos(carpeta):
    version = carpeta / VERSION
    version.mkdir(parents=True, exist_ok=True)
    (version / "runesReforged.json").write_text(json.dumps(RUNAS, ensure_ascii=False), encoding="utf-8")
    (version / "summoner.json").write_text(json.dumps(HECHIZOS, ensure_ascii=False), encoding="utf-8")


def test_comando_exportar_escribe_los_seis_archivos(api, tmp_path, monkeypatch):
    datos = tmp_path / "data"
    datos.mkdir()
    _base(api, datos)
    _estaticos_falsos(datos / "estaticos")
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(datos))
    monkeypatch.chdir(tmp_path)

    assert cli.main(["exportar"]) == 0

    destino = tmp_path / "docs" / "data"
    for nombre in ("meta.json", "partidas.json", "curvas.json", "muertes.json", "compras.json", "estaticos.json"):
        assert (destino / nombre).exists(), nombre
    assert len(json.loads((destino / "partidas.json").read_text(encoding="utf-8"))) == 3


def test_comando_exportar_avisa_si_no_hay_base(tmp_path, monkeypatch):
    datos = tmp_path / "data"
    datos.mkdir()
    monkeypatch.setenv("PREPARTIDA_DATA_DIR", str(datos))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["exportar"]) == 2


def _repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "docs" / "data").mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Prueba")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "prueba@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Prueba")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "prueba@example.com")
    monkeypatch.chdir(repo)
    return repo


def test_publicar_en_git_hace_commit_y_avisa_que_no_hay_remoto(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path, monkeypatch)
    (repo / "docs" / "data" / "meta.json").write_text("{}\n", encoding="utf-8")

    assert cli._publicar_en_git(repo / "docs" / "data") == 0

    salida = capsys.readouterr().out
    assert "se omite el push" in salida
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert "datos:" in log


def test_publicar_en_git_no_hace_commit_sin_cambios(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path, monkeypatch)
    (repo / "docs" / "data" / "meta.json").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "docs/data"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "datos: base"], cwd=repo, check=True)

    assert cli._publicar_en_git(repo / "docs" / "data") == 0

    assert "no cambiaron" in capsys.readouterr().out
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True
    ).stdout.strip().splitlines()
    assert len(log) == 1


def test_publicar_en_git_no_incluye_archivo_ajeno_preparado(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path, monkeypatch)
    (repo / "docs" / "data" / "meta.json").write_text("{}\n", encoding="utf-8")
    ajeno = repo / "nota.txt"
    ajeno.write_text("otro\n", encoding="utf-8")
    subprocess.run(["git", "add", "nota.txt"], cwd=repo, check=True)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Prueba")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "prueba@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Prueba")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "prueba@example.com")
    monkeypatch.chdir(repo)

    assert cli._publicar_en_git(repo / "docs" / "data") == 0

    archivos = subprocess.run(
        ["git", "show", "--stat", "--format=", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert "docs/data/meta.json" in archivos
    assert "nota.txt" not in archivos
