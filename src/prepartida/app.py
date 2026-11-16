"""App web local. Se abre con: prepartida app"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from prepartida import db, estado, ingest, metricas
from prepartida.config import leer_config
from prepartida.perfil import leer_perfil
from prepartida.riot_client import RiotClient, RiotError

st.set_page_config(page_title="Prepartida", layout="wide")

cfg = leer_config()
perfil = leer_perfil()


def cargar() -> tuple[tuple | None, tuple | None, pd.DataFrame]:
    """Lee todo lo necesario y cierra la conexión, para no bloquear la base."""
    con = db.conectar(cfg.db_path)
    try:
        jugador = con.execute(
            "SELECT puuid, game_name, tag_line FROM jugador ORDER BY actualizado DESC LIMIT 1"
        ).fetchone()
        if jugador is None:
            return None, None, pd.DataFrame()
        rango = estado.rango_actual(con, jugador[0])
        return jugador, rango, metricas.partidas_del_jugador(con, jugador[0], perfil)
    finally:
        con.close()


def actualizar() -> str:
    client = RiotClient(cfg.api_key, cfg.platform, cfg.region)
    con = db.conectar(cfg.db_path)
    try:
        puuid = ingest.ingerir_perfil(client, con, cfg.game_name, cfg.tag_line)
        r = ingest.ingerir_historial(client, con, puuid, raw_dir=cfg.raw_dir)
        return f"{r['nuevas']} partidas nuevas"
    finally:
        con.close()
        client.close()


def tabla(df: pd.DataFrame, nombre_indice: str | None = None) -> None:
    if nombre_indice is not None:
        df = df.rename_axis(nombre_indice).reset_index()
    st.dataframe(
        df.rename(
            columns={
                "campeon": "Campeón",
                "posicion": "Posición",
                "partidas": "Partidas",
                "victorias": "Victorias",
                "tasa": "Tasa %",
                "tasa_ajustada": "Tasa ajustada %",
                "cs_10": "CS al 10",
                "dif_oro_15": "Oro al 15 vs. rival",
                "muertes_14": "Muertes antes del 14",
            }
        ),
        hide_index=True,
        width="stretch",
    )


st.title("Prepartida")

with st.sidebar:
    st.subheader("Datos")
    if st.button("Actualizar partidas"):
        try:
            with st.spinner("Descargando de la API de Riot..."):
                st.success(actualizar())
        except RiotError as e:
            st.error(f"Error de la API de Riot: {e}")
    st.caption(f"Base: {cfg.db_path}")
    st.subheader("Perfil")
    st.write("Pool: " + ", ".join(perfil.pool))
    st.caption("Se edita en perfil.toml")

jugador, rango, df = cargar()

if jugador is None or df.empty:
    st.info("Aún no hay partidas en la base. Usa «Actualizar partidas» o ejecuta `prepartida ingesta`.")
    st.stop()

_, nombre, tag = jugador
linea_rango = ""
if rango:
    tier, division, lp, v, d = rango
    linea_rango = f" · {tier} {division}, {lp} LP ({v} victorias, {d} derrotas)"
st.subheader(f"{nombre} #{tag}{linea_rango}")

# --- Aviso de sesión ---
hoy = metricas.partidas_de_hoy(df, perfil)
if len(hoy) >= perfil.partidas_por_sesion:
    st.warning(
        f"Llevas {len(hoy)} partidas hoy ({int(hoy['victoria'].sum())} ganadas). "
        f"Tu meta es parar en {perfil.partidas_por_sesion}."
    )
elif len(hoy) > 0:
    st.caption(f"Hoy: {len(hoy)} partidas, {int(hoy['victoria'].sum())} ganadas.")

# --- Cifras principales ---
r = metricas.resumen(df)
pvf = metricas.pool_vs_fuera(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidas en la base", r["partidas"], f"{r['victorias']} ganadas", delta_color="off")
c2.metric(
    "CS al minuto 10",
    r["cs_10"],
    f"{r['cs_10'] - perfil.meta_cs_10:+.1f} vs. meta de {perfil.meta_cs_10}",
)
c3.metric(
    "Oro al 15 vs. rival de línea",
    f"{r['dif_oro_15']:+d}" if r["dif_oro_15"] is not None else "-",
    f"por detrás en {r['por_detras_15']} de {r['con_dato_15']}",
    delta_color="off",
)
c4.metric(
    "Muertes antes del 14",
    r["muertes_14"],
    f"{r['muertes_14'] - perfil.meta_muertes_14:+.2f} vs. meta de {perfil.meta_muertes_14}",
    delta_color="inverse",
)

# --- Estado del pool ---
st.header("Estado de tu pool")
en_pool = df[df["en_pool"]]
tabla(metricas.por_campeon(en_pool))
st.caption(
    f"La tasa ajustada se contrae hacia el 50 % (equivale a sumar {metricas.PRIOR_PARTIDAS} "
    f"partidas ficticias). Con menos de {metricas.MUESTRA_MINIMA} partidas, toma la fila como indicio."
)

izq, der = st.columns(2)
with izq:
    st.subheader("Pool vs. fuera del pool")
    tabla(pvf, "Grupo")
    st.subheader("Por posición")
    tabla(metricas.por_posicion(df), "Posición")
with der:
    st.subheader("Según muertes antes del minuto 14")
    tabla(metricas.por_muertes_tempranas(df), "Muertes")
    st.subheader("Según el orden de la partida en el día")
    tabla(metricas.por_orden_en_sesion(df, perfil.partidas_por_sesion), "Tramo")

fuera = df[~df["en_pool"]]
if not fuera.empty:
    with st.expander(f"Campeones fuera del pool ({len(fuera)} partidas)"):
        tabla(metricas.por_campeon(fuera))

# --- Últimas partidas ---
st.header("Últimas partidas")
ultimas = df.sort_values("inicio", ascending=False).head(15).copy()
ultimas["Fecha"] = (ultimas["inicio"] - pd.Timedelta(hours=5)).dt.strftime("%Y-%m-%d %H:%M")
ultimas["Resultado"] = ultimas["victoria"].map({True: "Victoria", False: "Derrota"})
ultimas["KDA"] = (
    ultimas["asesinatos"].astype(str) + "/" + ultimas["muertes"].astype(str) + "/" + ultimas["asistencias"].astype(str)
)
st.dataframe(
    ultimas[
        ["Fecha", "Resultado", "campeon", "posicion", "rival", "lado", "KDA", "cs_10", "dif_oro_15", "muertes_14"]
    ].rename(
        columns={
            "campeon": "Campeón",
            "posicion": "Posición",
            "rival": "Rival",
            "lado": "Lado",
            "cs_10": "CS al 10",
            "dif_oro_15": "Oro al 15 vs. rival",
            "muertes_14": "Muertes antes del 14",
        }
    ),
    hide_index=True,
    width="stretch",
)
