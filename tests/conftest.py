"""API de Riot simulada para las pruebas (sin red)."""

from __future__ import annotations

import httpx
import pytest

PUUID = "puuid-yo"


def partida_falsa(match_id: str, gano: bool, campeon: str = "Ahri") -> dict:
    participantes = []
    for i in range(1, 11):
        equipo = 100 if i <= 5 else 200
        posicion = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][(i - 1) % 5]
        yo = i == 3
        participantes.append(
            {
                "participantId": i,
                "puuid": PUUID if yo else f"otro-{i}",
                "teamId": equipo,
                "championId": 103 if yo else i,
                "championName": campeon if yo else f"Campeon{i}",
                "teamPosition": posicion,
                "win": gano if equipo == 100 else not gano,
                "kills": 5,
                "deaths": 2,
                "assists": 7,
                "totalMinionsKilled": 180,
                "neutralMinionsKilled": 10,
                "goldEarned": 11000,
                "totalDamageDealtToChampions": 20000,
                "visionScore": 18,
                **{f"item{n}": 3000 + n for n in range(7)},
                "summoner1Id": 4,
                "summoner2Id": 14,
                "perks": {
                    "styles": [
                        {"style": 8100, "selections": [{"perk": 8112}]},
                        {"style": 8200, "selections": [{"perk": 8226}]},
                    ]
                },
            }
        )
    return {
        "metadata": {"matchId": match_id},
        "info": {
            "gameVersion": "16.22.701.1234",
            "queueId": 420,
            "gameCreation": 1794000000000,
            "gameDuration": 1800,
            "teams": [{"teamId": 100, "win": gano}, {"teamId": 200, "win": not gano}],
            "participants": participantes,
        },
    }


def linea_falsa(match_id: str) -> dict:
    cuadros = []
    for minuto in range(0, 17):
        pf = {
            str(i): {
                "totalGold": 500 + minuto * (400 if i == 3 else 350),
                "xp": minuto * 300,
                "minionsKilled": minuto * 7,
                "jungleMinionsKilled": 0,
                "position": {"x": 7000, "y": 7000},
            }
            for i in range(1, 11)
        }
        eventos = (
            [{"type": "CHAMPION_KILL", "timestamp": 300000, "killerId": 3, "victimId": 8}]
            if minuto == 5
            else []
        )
        cuadros.append({"participantFrames": pf, "events": eventos})
    return {"metadata": {"matchId": match_id}, "info": {"frames": cuadros}}


class ApiFalsa:
    def __init__(self) -> None:
        self.ids = ["LA1_1", "LA1_2", "LA1_3"]
        self.resultados = {"LA1_1": True, "LA1_2": False, "LA1_3": True}
        self.llamadas: list[str] = []
        self.fallos_429 = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        ruta = request.url.path
        self.llamadas.append(f"{request.url.host}{ruta}")
        if request.headers.get("X-Riot-Token") != "clave-buena":
            return httpx.Response(403, json={"status": {"message": "Forbidden"}})
        if self.fallos_429 > 0:
            self.fallos_429 -= 1
            return httpx.Response(429, headers={"Retry-After": "3"})
        if "/accounts/by-riot-id/" in ruta:
            return httpx.Response(
                200, json={"puuid": PUUID, "gameName": "SithLordDropout", "tagLine": "LAN"}
            )
        if "/league/v4/entries/by-puuid/" in ruta:
            return httpx.Response(
                200,
                json=[
                    {
                        "queueType": "RANKED_SOLO_5x5",
                        "tier": "BRONZE",
                        "rank": "III",
                        "leaguePoints": 40,
                        "wins": 30,
                        "losses": 32,
                    }
                ],
            )
        if "/lol/league/v4/entries/RANKED_SOLO_5x5/" in ruta:
            partes = ruta.split("/lol/league/v4/entries/RANKED_SOLO_5x5/")[1].split("?")[0].split("/")
            tier = partes[0]
            division = partes[1]
            pagina = int(request.url.params.get("page", 1))
            if pagina > 3:
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "puuid": f"puuid-{tier}-{division}-{pagina}-1",
                        "tier": tier,
                        "rank": division,
                        "leaguePoints": 100,
                    },
                    {
                        "puuid": f"puuid-{tier}-{division}-{pagina}-2",
                        "tier": tier,
                        "rank": division,
                        "leaguePoints": 90,
                    },
                ],
            )
        if "/champion-masteries/by-puuid/" in ruta:
            return httpx.Response(
                200,
                json=[
                    {
                        "championId": 103,
                        "championLevel": 9,
                        "championPoints": 90000,
                        "lastPlayTime": 1794000000000,
                    }
                ],
            )
        if ruta.endswith("/ids"):
            inicio = int(request.url.params.get("start", 0))
            cantidad = int(request.url.params.get("count", 20))
            return httpx.Response(200, json=self.ids[inicio : inicio + cantidad])
        if ruta.endswith("/timeline"):
            match_id = ruta.split("/")[-2]
            return httpx.Response(200, json=linea_falsa(match_id))
        if "/match/v5/matches/" in ruta:
            match_id = ruta.split("/")[-1]
            return httpx.Response(200, json=partida_falsa(match_id, self.resultados[match_id]))
        return httpx.Response(404)


@pytest.fixture
def api() -> ApiFalsa:
    return ApiFalsa()
