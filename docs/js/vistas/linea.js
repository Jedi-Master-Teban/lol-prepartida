/* Vista Línea (sección 1b, T08 de PLAN.md).
   Recibe datos ya calculados y solo dibuja. */

import { curvaPromedio } from "../calc.js";
import { token } from "../tema.js";

function formatoNumero(valor, decimales = 1) {
  if (valor == null) return "—";
  return valor.toFixed(decimales);
}

function numeroConSigno(valor) {
  if (valor == null) return "—";
  return valor > 0 ? "+" + valor : String(valor).replace("-", "\u2212");
}

function tasaCruda(victorias, partidas) {
  if (!partidas) return 0;
  return Math.round((100 * victorias) / partidas * 10) / 10;
}

function oroMedio(partidas) {
  const conDato = partidas.filter((p) => p.dif_oro_15 != null);
  if (conDato.length === 0) return null;
  const suma = conDato.reduce((a, b) => a + b.dif_oro_15, 0);
  return Math.round(suma / conDato.length);
}

function agruparPorMuertes(partidas) {
  const grupos = { "0": [], "1": [], "2": [] };
  for (const p of partidas) {
    const clave = p.muertes_14 >= 2 ? "2" : String(p.muertes_14);
    grupos[clave].push(p);
  }
  return grupos;
}

function opcionesPosiciones(partidas) {
  const vista = new Set();
  for (const p of partidas) {
    if (p.posicion) vista.add(p.posicion);
  }
  return [...vista].sort();
}

export function render(container, datos) {
  const { partidas, curvas, meta } = datos;
  const metaCs10 = meta.perfil.meta_cs_10;
  const pool = meta.perfil.pool;
  container.innerHTML = "";

  // --- Selectores ---
  const selectores = document.createElement("div");
  selectores.className = "selectores fila";

  const selCampeon = document.createElement("select");
  selCampeon.className = "select-campeon";
  selCampeon.innerHTML = `<option value="Todos">Todos los campeones</option>`;
  for (const c of pool) {
    selCampeon.innerHTML += `<option value="${c}">${c}</option>`;
  }

  const selPosicion = document.createElement("select");
  selPosicion.className = "select-posicion";
  selPosicion.innerHTML = `<option value="Todas">Todas las posiciones</option>`;
  for (const pos of opcionesPosiciones(partidas)) {
    selPosicion.innerHTML += `<option value="${pos}">${pos}</option>`;
  }

  const lblCampeon = document.createElement("label");
  lblCampeon.textContent = "Campeón: ";
  lblCampeon.appendChild(selCampeon);

  const lblPosicion = document.createElement("label");
  lblPosicion.textContent = " Posición: ";
  lblPosicion.appendChild(selPosicion);

  selectores.appendChild(lblCampeon);
  selectores.appendChild(lblPosicion);
  container.appendChild(selectores);

  // --- Contenedores de gráficas ---
  const graficas = document.createElement("div");
  graficas.className = "graficas fila";
  container.appendChild(graficas);

  const colOro = document.createElement("div");
  colOro.className = "col";
  colOro.innerHTML = `
    <h3>Oro vs rival (0-20 min)</h3>
    <p class="cuenta-oro suave"></p>
    <div class="grafica"><canvas id="grafica-oro"></canvas></div>
  `;
  const colCs = document.createElement("div");
  colCs.className = "col";
  colCs.innerHTML = `
    <h3>CS acumulado (0-20 min)</h3>
    <p class="cuenta-cs suave"></p>
    <div class="grafica"><canvas id="grafica-cs"></canvas></div>
  `;
  const colMuertes = document.createElement("div");
  colMuertes.className = "col";
  colMuertes.innerHTML = `
    <h3>Según muertes tempranas</h3>
    <p class="cuenta-muertes suave"></p>
    <div class="grafica barras-muertes"><canvas id="grafica-muertes"></canvas></div>
  `;
  graficas.appendChild(colOro);
  graficas.appendChild(colCs);
  graficas.appendChild(colMuertes);

  let chartOro = null;
  let chartCs = null;
  let chartMuertes = null;

  function destruirGraficas() {
    if (chartOro) { chartOro.destroy(); chartOro = null; }
    if (chartCs) { chartCs.destroy(); chartCs = null; }
    if (chartMuertes) { chartMuertes.destroy(); chartMuertes = null; }
  }

  function dibujar(filtrados) {
    destruirGraficas();
    const ids = filtrados.map((p) => p.match_id);
    const n = filtrados.length;

    const cuentaOro = colOro.querySelector(".cuenta-oro");
    cuentaOro.textContent = `Promedio de ${n} partida${n !== 1 ? "s" : ""}`;
    const cuentaCs = colCs.querySelector(".cuenta-cs");
    cuentaCs.textContent = `Promedio de ${n} partida${n !== 1 ? "s" : ""}`;
    const cuentaMuertes = colMuertes.querySelector(".cuenta-muertes");
    cuentaMuertes.textContent = `Promedio de ${n} partida${n !== 1 ? "s" : ""}`;

    // --- Chart 1: Diferencia de oro frente al rival (0-20 min) ---
    const difOro = curvaPromedio(curvas, ids, "dif_oro", 20);
    const difPos = difOro.map((v) => (v != null && v > 0 ? v : 0));
    const difNeg = difOro.map((v) => (v != null && v < 0 ? v : 0));
    const difLine = difOro.map((v) => (v != null ? v : null));

    const ctxOro = document.getElementById("grafica-oro").getContext("2d");
    chartOro = new Chart(ctxOro, {
      type: "line",
      data: {
        labels: difOro.map((_, i) => i),
        datasets: [
          {
            label: "A favor",
            data: difPos,
            backgroundColor: token("victoria"),
            borderWidth: 0,
            pointRadius: 0,
            fill: "origin",
            showInLegend: false
          },
          {
            label: "En contra",
            data: difNeg,
            backgroundColor: token("derrota"),
            borderWidth: 0,
            pointRadius: 0,
            fill: "origin",
            showInLegend: false
          },
          {
            label: "Oro vs rival",
            data: difLine,
            borderColor: token("texto"),
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.15
          },
          {
            label: "Cero",
            data: difOro.map(() => 0),
            borderColor: token("borde"),
            borderDash: [6, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            showInLegend: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: { display: false },
          tooltip: {
            mode: "index",
            intersect: false
          }
        },
        scales: {
          x: {
            type: "linear",
            title: { display: true, text: "Minuto", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
            min: 0,
            max: 20
          },
          y: {
            title: { display: true, text: "Diferencia de oro", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") }
          }
        },
        animation: { duration: 0 }
      }
    });

    // --- Chart 2: CS acumulado (0-20 min) ---
    const cs = curvaPromedio(curvas, ids, "cs", 20);
    const pendiente = metaCs10 / 10;
    const metaLine = cs.map((_, i) => i * pendiente);

    const ctxCs = document.getElementById("grafica-cs").getContext("2d");
    chartCs = new Chart(ctxCs, {
      type: "line",
      data: {
        labels: cs.map((_, i) => i),
        datasets: [
          {
            label: "CS acumulado",
            data: cs,
            borderColor: token("texto"),
            backgroundColor: "rgba(230, 235, 245, 0.1)",
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.15
          },
          {
            label: `Meta ${metaCs10}`,
            data: metaLine,
            borderColor: token("acento"),
            backgroundColor: "transparent",
            borderWidth: 2,
            borderDash: [6, 4],
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color: token("texto-suave"), font: { size: 12 } } },
          title: { display: false },
          tooltip: { mode: "index", intersect: false }
        },
        scales: {
          x: {
            type: "linear",
            title: { display: true, text: "Minuto", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
            min: 0,
            max: 20
          },
          y: {
            title: { display: true, text: "CS acumulado", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
            beginAtZero: true
          }
        },
        animation: { duration: 0 }
      }
    });

    // --- Chart 3: Según muertes tempranas ---
    const grupos = agruparPorMuertes(filtrados);
    const categorias = ["0 muertes", "1 muerte", "2 o más muertes"];
    const claves = ["0", "1", "2"];
    const tasas = claves.map((k) => {
      const g = grupos[k];
      return tasaCruda(g.filter((p) => p.victoria).length, g.length);
    });
    const orosMedios = claves.map((k) => oroMedio(grupos[k]));
    const conteos = claves.map((k) => grupos[k].length);

    const ctxMuertes = document.getElementById("grafica-muertes").getContext("2d");
    chartMuertes = new Chart(ctxMuertes, {
      type: "bar",
      data: {
        labels: categorias,
        datasets: [
          {
            label: "Tasa de victorias",
            data: tasas,
            backgroundColor: [
              tasas[0] >= 50 ? token("victoria") : token("derrota"),
              tasas[1] >= 50 ? token("victoria") : token("derrota"),
              tasas[2] >= 50 ? token("victoria") : token("derrota")
            ],
            borderWidth: 0,
            borderRadius: 4
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const i = ctx.dataIndex;
                return `${conteos[i]} partidas · oro medio ${numeroConSigno(orosMedios[i])}`;
              }
            }
          }
        },
        scales: {
          x: {
            min: 0,
            max: 100,
            title: { display: true, text: "Tasa de victorias (%)", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") }
          },
          y: {
            grid: { display: false },
            ticks: { color: token("texto"), font: { size: 12 } }
          }
        },
        animation: { duration: 0 }
      }
    });

    // Añadir etiquetas con conteo y oro bajo cada barra del eje Y no aplica en indexAxis: "y".
    // Usar tooltip en su lugar.
  }

  // Dibujar inicial con todos los partidos
  dibujar(partidas);

  // Event listeners de selectores
  selCampeon.addEventListener("change", () => {
    const campeon = selCampeon.value;
    const posicion = selPosicion.value;
    dibujar(filtrar(partidas, campeon, posicion));
  });
  selPosicion.addEventListener("change", () => {
    const campeon = selCampeon.value;
    const posicion = selPosicion.value;
    dibujar(filtrar(partidas, campeon, posicion));
  });
}
