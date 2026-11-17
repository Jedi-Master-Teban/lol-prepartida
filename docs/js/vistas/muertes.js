/* Vista Muertes (sección 1b, T09 de PLAN.md).
   Recibe datos ya calculados y solo dibuja. */

import { aCoordenadaMapa } from "../calc.js";
import { urlMinimapa } from "../imagenes.js";
import { token } from "../tema.js";

function formatoNumero(valor, decimales = 1) {
  if (valor == null) return "—";
  return valor.toFixed(decimales);
}

export function render(container, datos) {
  const { partidas, muertes, meta, estaticos } = datos;
  const version = meta.version_ddragon;
  container.innerHTML = "";

  // Lookup: clave de campeón → nombre visible (p. ej. "MissFortune" → "Miss Fortune")
  const nombreCampeon = {};
  for (const [id, info] of Object.entries(estaticos.campeones || {})) {
    if (info.clave) nombreCampeon[info.clave] = info.nombre;
  }

  // Campeones del pool para el filtro
  const campeonesPool = [...new Set(partidas.filter(p => p.en_pool).map(p => p.campeon))].sort();

  // --- Estado de filtros ---
  let filtroCampeon = "pool";
  let filtroLado = "todos";
  let filtroTiempo = "0-14";

  // --- Selectores ---
  const selectores = document.createElement("div");
  selectores.className = "selectores fila";

  const lblCampeon = document.createElement("label");
  lblCampeon.textContent = "Campeón: ";
  const selCampeon = document.createElement("select");
  selCampeon.innerHTML = `
    <option value="pool" selected>Todo el pool</option>
    <option value="todas">Todas las partidas</option>
  `;
  for (const c of campeonesPool) {
    selCampeon.innerHTML += `<option value="${c}">${c}</option>`;
  }
  lblCampeon.appendChild(selCampeon);
  selectores.appendChild(lblCampeon);

  const lblLado = document.createElement("label");
  lblLado.textContent = " Lado: ";
  const selLado = document.createElement("select");
  selLado.innerHTML = `
    <option value="todos">Todos</option>
    <option value="azul">Azul</option>
    <option value="rojo">Rojo</option>
  `;
  lblLado.appendChild(selLado);
  selectores.appendChild(lblLado);

  const lblTiempo = document.createElement("label");
  lblTiempo.textContent = " Tiempo: ";
  const selTiempo = document.createElement("select");
  selTiempo.innerHTML = `
    <option value="0-14" selected>0–14 min</option>
    <option value="14-25">14–25 min</option>
    <option value="25+">25+ min</option>
  `;
  lblTiempo.appendChild(selTiempo);
  selectores.appendChild(lblTiempo);

  container.appendChild(selectores);

  // --- Contenido principal ---
  const contenido = document.createElement("div");
  contenido.className = "muertes-contenido";
  container.appendChild(contenido);

  // Minimapa
  const mapaDiv = document.createElement("div");
  mapaDiv.className = "minimapa";

  const imgMapa = document.createElement("img");
  imgMapa.src = urlMinimapa(version);
  imgMapa.alt = "Minimapa";
  imgMapa.style.width = "100%";
  imgMapa.style.height = "100%";
  imgMapa.style.display = "block";
  mapaDiv.appendChild(imgMapa);

  const puntosDiv = document.createElement("div");
  puntosDiv.className = "puntos";
  puntosDiv.style.position = "relative";
  puntosDiv.style.width = "100%";
  puntosDiv.style.height = "100%";
  mapaDiv.appendChild(puntosDiv);

  contenido.appendChild(mapaDiv);

  // Leyenda y conteos (fuera del mapa, junto a los conteos)
  const infoDiv = document.createElement("div");
  infoDiv.className = "muertes-info";

  const leyendaDiv = document.createElement("div");
  leyendaDiv.className = "leyenda-mapa";
  const puntoVictoria = document.createElement("span");
  puntoVictoria.className = "punto-leyenda";
  puntoVictoria.style.backgroundColor = token("victoria");
  const lblVictoria = document.createElement("span");
  lblVictoria.textContent = "Victoria";
  const puntoDerrota = document.createElement("span");
  puntoDerrota.className = "punto-leyenda";
  puntoDerrota.style.backgroundColor = token("derrota");
  const lblDerrota = document.createElement("span");
  lblDerrota.textContent = "Derrota";
  leyendaDiv.appendChild(puntoVictoria);
  leyendaDiv.appendChild(lblVictoria);
  leyendaDiv.appendChild(puntoDerrota);
  leyendaDiv.appendChild(lblDerrota);

  const conteoMuertes = document.createElement("div");
  conteoMuertes.className = "conteo";

  const conteoPartidas = document.createElement("div");
  conteoPartidas.className = "conteo";

  infoDiv.appendChild(leyendaDiv);
  infoDiv.appendChild(conteoMuertes);
  infoDiv.appendChild(conteoPartidas);

  contenido.appendChild(infoDiv);

  // --- Filtrar y render ---
  function filtrarYRender() {
    puntosDiv.innerHTML = "";

    let muertesFiltradas = muertes;

    if (filtroCampeon === "todas") {
      // No filtro por campeón
    } else if (filtroCampeon === "pool") {
      muertesFiltradas = muertesFiltradas.filter(m => {
        const info = matchLookup[m.match_id];
        return info && info.en_pool;
      });
    } else {
      muertesFiltradas = muertesFiltradas.filter(m => {
        const info = matchLookup[m.match_id];
        return info && info.campeon === filtroCampeon;
      });
    }

    if (filtroLado !== "todos") {
      muertesFiltradas = muertesFiltradas.filter(m => {
        const info = matchLookup[m.match_id];
        return info && info.lado === filtroLado;
      });
    }

    muertesFiltradas = muertesFiltradas.filter(m => {
      const min = m.minuto;
      if (filtroTiempo === "0-14") return min >= 0 && min < 14;
      if (filtroTiempo === "14-25") return min >= 14 && min < 25;
      if (filtroTiempo === "25+") return min >= 25;
      return true;
    });

    const matchIds = [...new Set(muertesFiltradas.map(m => m.match_id))];

    conteoMuertes.textContent = `Muertes mostradas: ${muertesFiltradas.length}`;
    conteoPartidas.textContent = `Partidas: ${matchIds.length}`;

    for (const m of muertesFiltradas) {
      const info = matchLookup[m.match_id];
      if (!info) continue;

      const { izquierda, arriba } = aCoordenadaMapa(m.x, m.y);

      const punto = document.createElement("div");
      punto.className = "punto";
      punto.style.left = `${izquierda}%`;
      punto.style.top = `${arriba}%`;
      punto.style.backgroundColor = info.victoria ? token("victoria") : token("derrota");

      punto.title = `${nombreCampeon[info.campeon] || info.campeon} vs ${nombreCampeon[info.rival] || info.rival} · ${formatoNumero(m.minuto)} min · ${info.victoria ? "Victoria" : "Derrota"}`;

      puntosDiv.appendChild(punto);
    }
  }

  selCampeon.addEventListener("change", (e) => {
    filtroCampeon = e.target.value;
    filtrarYRender();
  });
  selLado.addEventListener("change", (e) => {
    filtroLado = e.target.value;
    filtrarYRender();
  });
  selTiempo.addEventListener("change", (e) => {
    filtroTiempo = e.target.value;
    filtrarYRender();
  });

  filtrarYRender();
}
