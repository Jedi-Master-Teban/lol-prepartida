from __future__ import annotations

import httpx
import pytest

from prepartida.riot_client import RateLimiter, RiotClient


def test_entradas_de_liga_ruta_y_parametros(api):
    """La ruta y los parámetros de página son correctos."""
    cliente = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    resultado = cliente.entradas_de_liga("GOLD", "II", pagina=2)
    assert len(resultado) == 2
    assert resultado[0]["tier"] == "GOLD"
    assert resultado[0]["rank"] == "II"
    # Verifica que se llamó a la ruta correcta
    assert any(
        llamada == "la1.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/GOLD/II"
        for llamada in api.llamadas
    )
    # Verifica que el parámetro page se pasó (la respuesta contiene datos de página 2)
    assert resultado[0]["puuid"] == "puuid-GOLD-II-2-1"


def test_entradas_de_liga_pagina_vacia_devuelve_lista_vacia(api):
    """Una página sin entradas devuelve lista vacía."""
    cliente = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    resultado = cliente.entradas_de_liga("GOLD", "II", pagina=4)
    assert resultado == []


def test_entradas_de_liga_pagina_uno(api):
    """La página uno devuelve las dos entradas simuladas."""
    cliente = RiotClient(
        "clave-buena",
        transport=httpx.MockTransport(api),
        limiter_factory=lambda: RateLimiter(sleep=lambda _s: None),
        sleep=lambda _s: None,
    )
    resultado = cliente.entradas_de_liga("PLATINUM", "I", pagina=1)
    assert len(resultado) == 2
    assert resultado[0]["tier"] == "PLATINUM"
    assert resultado[0]["rank"] == "I"
