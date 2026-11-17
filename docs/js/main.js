/* Carga de datos, cabecera fija y navegación por pestañas (fragmento de URL).
   Orquesta las vistas: cada una expone render(container, datos). */

import { cargarDatos } from "./datos.js";
import * as vistaInicio from "./vistas/inicio.js";
import * as vistaPool from "./vistas/pool.js";
import * as vistaLinea from "./vistas/linea.js";
import * as vistaMuertes from "./vistas/muertes.js";
import * as vistaPartidas from "./vistas/partidas.js";
import { token } from "./tema.js";

Chart.defaults.color = token("texto-suave");
Chart.defaults.borderColor = token("borde");

const SECCIONES = ["inicio", "pool", "linea", "muertes", "partidas"];
const VISTAS = {
  inicio: vistaInicio,
  pool: vistaPool,
  linea: vistaLinea,
  muertes: vistaMuertes,
  partidas: vistaPartidas,
};

const cabecera = document.querySelector(".cabecera .contenido");
const nombreEl = document.querySelector(".nombre");
const rangoEl = document.querySelector(".rango");
const actualizadoEl = document.querySelector(".actualizado");
const errorEl = document.getElementById("error-carga");

let datos = null;

export function obtenerDatos() {
  return datos;
}

function mostrarError(mensaje) {
  if (errorEl) {
    errorEl.textContent = mensaje;
    errorEl.style.display = "block";
  }
  console.error(mensaje);
}

const TIER_ESPANOL = {
  IRON: "Hierro",
  BRONZE: "Bronce",
  SILVER: "Plata",
  GOLD: "Oro",
  PLATINUM: "Platino",
  EMERALD: "Esmeralda",
  DIAMOND: "Diamante",
  MASTER: "Maestro",
  GRANDMASTER: "Gran Maestro",
  CHALLENGER: "Retador",
};

function renderCabecera(meta) {
  const jugador = meta.jugador;
  const tierTexto = jugador.tier ? TIER_ESPANOL[jugador.tier] || jugador.tier : "";
  const partes = [tierTexto, jugador.division, jugador.lp != null ? `${jugador.lp} LP` : null].filter(Boolean);
  const rango = partes.length ? partes.join(" · ") : "Sin rango";
  nombreEl.textContent = `${jugador.game_name} #${jugador.tag_line}`;
  rangoEl.textContent = `${rango} · ${jugador.victorias} victorias, ${jugador.derrotas} derrotas`;
  const fecha = new Date(meta.generado).toLocaleString("es-ES", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  actualizadoEl.textContent = `Actualizado: ${fecha}`;
}

function seccionActiva() {
  const hash = location.hash.replace(/^#/, "") || "inicio";
  return SECCIONES.includes(hash) ? hash : "inicio";
}

function renderVista(activa) {
  const vista = VISTAS[activa];
  const container = document.getElementById(`vista-${activa}`);
  if (vista && vista.render && container && datos) {
    vista.render(container, datos);
  }
}

function navegar() {
  const activa = seccionActiva();
  SECCIONES.forEach((id) => {
    const el = document.getElementById(id);
    const link = document.querySelector(`.nav a[href="#${id}"]`);
    if (el) el.classList.toggle("activa", id === activa);
    if (link) link.classList.toggle("activa", id === activa);
  });
  renderVista(activa);
  window.dispatchEvent(new CustomEvent("cambiaseccion", { detail: { seccion: activa } }));
}

async function init() {
  try {
    datos = await cargarDatos();
    renderCabecera(datos.meta);
  } catch (error) {
    mostrarError(
      "No se pudieron cargar los datos. Asegúrate de haber ejecutado `prepartida exportar`."
    );
    return;
  }

  window.addEventListener("hashchange", navegar);
  window.addEventListener("load", navegar);
  navegar();
}

init();
