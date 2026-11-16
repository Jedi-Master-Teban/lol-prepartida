"""Cliente de la API de Riot con limitador de tasa.

Límites de una clave personal o de desarrollo: 20 peticiones por segundo y
100 cada 2 minutos, aplicados por valor de enrutamiento (la1, americas, ...).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable
from urllib.parse import quote

import httpx

LIMITES_POR_DEFECTO: tuple[tuple[int, float], ...] = ((20, 1.0), (100, 120.0))
COLA_SOLO_DUO = 420


class RiotError(Exception):
    """Error genérico de la API de Riot."""


class ClaveInvalida(RiotError):
    """La clave falta, expiró o no tiene permiso (códigos 401 y 403)."""


class NoEncontrado(RiotError):
    """El recurso no existe (código 404)."""


class RateLimiter:
    """Ventanas deslizantes: bloquea hasta que la petición cabe en todas."""

    def __init__(
        self,
        limites: tuple[tuple[int, float], ...] = LIMITES_POR_DEFECTO,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.limites = limites
        self._clock = clock
        self._sleep = sleep
        self._marcas: deque[float] = deque()
        self._ventana_max = max(v for _, v in limites)

    def acquire(self) -> None:
        while True:
            ahora = self._clock()
            while self._marcas and ahora - self._marcas[0] >= self._ventana_max:
                self._marcas.popleft()
            espera = 0.0
            for cupo, ventana in self.limites:
                recientes = [t for t in self._marcas if ahora - t < ventana]
                if len(recientes) >= cupo:
                    espera = max(espera, recientes[-cupo] + ventana - ahora)
            if espera <= 0:
                self._marcas.append(ahora)
                return
            self._sleep(espera)


class RiotClient:
    def __init__(
        self,
        api_key: str,
        platform: str = "la1",
        region: str = "americas",
        transport: httpx.BaseTransport | None = None,
        limiter_factory: Callable[[], RateLimiter] = RateLimiter,
        sleep: Callable[[float], None] = time.sleep,
        max_reintentos: int = 5,
    ) -> None:
        if not api_key:
            raise ClaveInvalida("Falta RIOT_API_KEY. Revisa el archivo .env.")
        self.platform = platform
        self.region = region
        self._http = httpx.Client(
            headers={"X-Riot-Token": api_key}, timeout=20.0, transport=transport
        )
        self._limiter_factory = limiter_factory
        self._limiters: dict[str, RateLimiter] = {}
        self._sleep = sleep
        self._max_reintentos = max_reintentos

    def close(self) -> None:
        self._http.close()

    def _get(self, enrutamiento: str, path: str, params: dict[str, Any] | None = None) -> Any:
        limiter = self._limiters.setdefault(enrutamiento, self._limiter_factory())
        url = f"https://{enrutamiento}.api.riotgames.com{path}"
        ultimo = ""
        for intento in range(self._max_reintentos):
            limiter.acquire()
            r = self._http.get(url, params=params)
            if r.status_code == 200:
                return r.json()
            ultimo = f"{r.status_code} en {path}"
            if r.status_code == 429:
                self._sleep(float(r.headers.get("Retry-After", "10")))
                continue
            if r.status_code in (500, 502, 503, 504):
                self._sleep(float(2**intento))
                continue
            if r.status_code in (401, 403):
                raise ClaveInvalida(
                    f"La API rechazó la clave ({ultimo}). Las claves de desarrollo expiran cada 24 h."
                )
            if r.status_code == 404:
                raise NoEncontrado(ultimo)
            raise RiotError(ultimo)
        raise RiotError(f"Sin respuesta válida tras {self._max_reintentos} intentos ({ultimo})")

    # --- Enrutamiento regional (americas) ---

    def cuenta_por_riot_id(self, game_name: str, tag_line: str) -> dict:
        return self._get(
            self.region,
            f"/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{quote(tag_line)}",
        )

    def ids_de_partidas(
        self,
        puuid: str,
        queue: int | None = COLA_SOLO_DUO,
        start: int = 0,
        count: int = 100,
        start_time: int | None = None,
    ) -> list[str]:
        params: dict[str, Any] = {"start": start, "count": count}
        if queue is not None:
            params["queue"] = queue
        if start_time is not None:
            params["startTime"] = start_time
        return self._get(self.region, f"/lol/match/v5/matches/by-puuid/{puuid}/ids", params)

    def partida(self, match_id: str) -> dict:
        return self._get(self.region, f"/lol/match/v5/matches/{match_id}")

    def linea_de_tiempo(self, match_id: str) -> dict:
        return self._get(self.region, f"/lol/match/v5/matches/{match_id}/timeline")

    # --- Enrutamiento por plataforma (la1) ---

    def ligas_por_puuid(self, puuid: str) -> list[dict]:
        return self._get(self.platform, f"/lol/league/v4/entries/by-puuid/{puuid}")

    def maestrias_por_puuid(self, puuid: str) -> list[dict]:
        return self._get(
            self.platform, f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        )
