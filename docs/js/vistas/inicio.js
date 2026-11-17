/* Vista Inicio (sección 1b, T06/T06b de PLAN.md).
   Recibe datos ya calculados y solo dibuja. */

import { agrupar, resumen, tendencia, tasaAjustada } from "../calc.js";
import { urlCampeonRetrato } from "../imagenes.js";

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

function formatoNumero(valor, decimales = 1) {
  if (valor == null) return "—";
  return valor.toFixed(decimales);
}

function numeroConSigno(valor) {
  if (valor == null) return "—";
  return valor > 0 ? "+" + valor : valor;
}

function diferenciaConMeta(valor, meta, decimales) {
  if (valor == null || meta == null) return "—";
  const diff = valor - meta;
  const abs = Math.abs(diff);
  if (abs === 0) return `en la meta de ${formatoNumero(meta, decimales)}`;
  const palabra = diff > 0 ? "por encima de la meta de" : "por debajo de la meta de";
  return `${formatoNumero(abs, decimales)} ${palabra} ${formatoNumero(meta, decimales)}`;
}

function crearSparkline(canvas, valores, color) {
  const ctx = canvas.getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: {
      datasets: [
        {
          data: valores.map((v, i) => ({ x: i, y: v })),
          borderColor: color,
          backgroundColor: "transparent",
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, title: { display: false } },
      scales: { x: { display: false }, y: { display: false } },
      animation: { duration: 0 },
    },
  });
}

function tarjetaIndicador(container, titulo, valorTexto, metaTexto, partidasTexto, valoresSpark, color) {
  const tarjeta = document.createElement("article");
  tarjeta.className = "tarjeta indicador";
  tarjeta.innerHTML = `
    <div class="valor grande">${valorTexto}</div>
    <div class="etiqueta">${titulo}</div>
    ${metaTexto ? `<div class="meta suave">${metaTexto}</div>` : ""}
    <div class="partidas suave">${partidasTexto}</div>
  `;
  const contenedor = document.createElement("div");
  contenedor.className = "minigrafica";
  const canvas = document.createElement("canvas");
  canvas.className = "spark";
  contenedor.appendChild(canvas);
  tarjeta.appendChild(contenedor);
  container.appendChild(tarjeta);
  if (valoresSpark && valoresSpark.some((v) => v != null)) {
    crearSparkline(canvas, valoresSpark, color);
  }
  return tarjeta;
}

export function render(container, datos) {
  const { meta, partidas } = datos;
  const perfil = meta.perfil;
  container.innerHTML = "";

  // --- Aviso de sesión ---
  const ahora = new Date();
  const referencia = new Date(ahora.getTime() - perfil.desfase_horas * 3600 * 1000);
  const diaHoy = referencia.toISOString().slice(0, 10);
  const partidasHoy = partidas.filter((p) => p.dia_sesion === diaHoy);
  if (partidasHoy.length >= perfil.partidas_por_sesion) {
    const ganadas = partidasHoy.filter((p) => p.victoria).length;
    const nodo = document.createElement("div");
    nodo.className = "tarjeta aviso-sesion";
    nodo.innerHTML = `<strong>Aviso de sesión:</strong> llevas ${partidasHoy.length} partida${
      partidasHoy.length !== 1 ? "s" : ""
    } (${ganadas} ganada${ganadas !== 1 ? "s" : ""}).`;
    container.appendChild(nodo);
  }

  // --- Cuatro indicadores ---
  const res = resumen(partidas);
  const ultimas30 = partidas.slice(-30);
  const sparkCs = tendencia(ultimas30, "cs_10", 3);
  const sparkOro = tendencia(ultimas30, "dif_oro_15", 3);
  const sparkMuertes = tendencia(ultimas30, "muertes_14", 3);

  const indicadores = document.createElement("div");
  indicadores.className = "indicadores fila";
  container.appendChild(indicadores);

  const csEnPool = agrupar(partidas, (p) => (p.en_pool ? "pool" : "fuera"));
  const grupoPool = csEnPool.find((g) => g.clave === "pool");
  const partidasPool = grupoPool ? grupoPool.partidas : 0;
  const victoriasPool = grupoPool ? grupoPool.victorias : 0;
  const tasaPool = grupoPool ? grupoPool.tasaAjustada : 0;

  tarjetaIndicador(
    indicadores,
    "CS al minuto 10",
    `${formatoNumero(res.cs10)}`,
    diferenciaConMeta(res.cs10, perfil.meta_cs_10, 1),
    `${res.partidas} partidas`,
    sparkCs,
    "var(--victoria)"
  );
  tarjetaIndicador(
    indicadores,
    "Oro al minuto 15",
    numeroConSigno(Math.round(res.difOro15 ?? 0)),
    `Por detrás en ${res.porDetras15} de ${res.conDato15}`,
    `${res.conDato15} partidas`,
    sparkOro,
    res.difOro15 < 0 ? "var(--derrota)" : "var(--victoria)"
  );
  tarjetaIndicador(
    indicadores,
    "Muertes antes del 14",
    formatoNumero(res.muertes14, 2),
    diferenciaConMeta(res.muertes14, perfil.meta_muertes_14, 2),
    `${res.partidas} partidas`,
    sparkMuertes,
    res.muertes14 > perfil.meta_muertes_14 ? "var(--derrota)" : "var(--victoria)"
  );
  tarjetaIndicador(
    indicadores,
    "Tasa dentro del pool",
    `${formatoNumero(tasaPool)} %`,
    `${victoriasPool} de ${partidasPool} ganadas`,
    `${partidasPool} partidas`,
    [],
    "var(--acento)"
  );

  // --- Franja del pool (bajo los indicadores) ---
  const franja = document.createElement("div");
  franja.className = "franja-pool";
  const etiqueta = document.createElement("div");
  etiqueta.className = "etiqueta-franja suave";
  etiqueta.textContent = "Tu pool:";
  franja.appendChild(etiqueta);
  const fila = document.createElement("div");
  fila.className = "carta-pool-fila";
  franja.appendChild(fila);
  const partidasPorCampeon = agrupar(partidas.filter((p) => p.en_pool), (p) => p.campeon);
  const porCampeon = {};
  for (const g of partidasPorCampeon) porCampeon[g.clave] = g;
  for (const campeon of perfil.pool) {
    const g = porCampeon[campeon];
    const n = g ? g.partidas : 0;
    const enlace = document.createElement("a");
    enlace.href = "#pool";
    enlace.className = "carta-pool";
    enlace.innerHTML = `
      <img class="retrato-pool" src="${urlCampeonRetrato(campeon, meta.version_ddragon)}" alt="${campeon}" onerror="this.style.display='none'; this.nextElementSibling.textContent='${campeon}';">
      <span class="nombre-pool-fallback" style="display:none">${campeon}</span>
      <div>
        <div class="nombre-pool">${campeon}</div>
        <div class="partidas-pool">${n} partida${n !== 1 ? "s" : ""}</div>
      </div>
    `;
    fila.appendChild(enlace);
  }
  container.appendChild(franja);

  // --- Gráfica de progreso: CS al 10 media móvil de 10 ---
  const progreso = document.createElement("div");
  progreso.className = "col";
  progreso.innerHTML = `<h3>CS al minuto 10</h3><div class="grafica"><canvas id="grafica-progreso"></canvas></div>`;
  container.appendChild(progreso);
  const ctxProgreso = document.getElementById("grafica-progreso").getContext("2d");
  const mediaMovil = tendencia(partidas, "cs_10", 10);
  const paso = Math.max(1, Math.round(partidas.length / 8));
  const etiquetas = [];
  const datosEtiqueta = [];
  for (let i = 0; i < partidas.length; i += paso) {
    etiquetas.push(i + 1);
    datosEtiqueta.push(mediaMovil[i]);
  }
  new Chart(ctxProgreso, {
    type: "line",
    data: {
      labels: etiquetas,
      datasets: [
        {
          label: "CS al minuto 10",
          data: datosEtiqueta,
          borderColor: "var(--texto)",
          backgroundColor: "rgba(230, 235, 245, 0.1)",
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.3,
        },
        {
          label: `Meta ${perfil.meta_cs_10}`,
          data: etiquetas.map(() => perfil.meta_cs_10),
          borderColor: "var(--acento)",
          backgroundColor: "transparent",
          borderWidth: 2,
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: "var(--texto-suave)", font: { size: 12 } } },
        title: {
          display: true,
          text: "CS al minuto 10 (últimas 30)",
          color: "var(--texto-suave)",
          font: { size: 14 },
        },
      },
      scales: {
        x: {
          display: true,
          grid: { color: "var(--borde)" },
          ticks: { color: "var(--texto-suave)", font: { size: 11 } },
          title: { display: true, text: "Partida", color: "var(--texto-suave)" },
        },
        y: {
          grid: { color: "var(--borde)" },
          ticks: { color: "var(--texto-suave)", font: { size: 11 } },
          title: {
            display: true,
            text: "CS al minuto 10",
            color: "var(--texto-suave)",
          },
        },
      },
      animation: { duration: 0 },
    },
  });

  // --- Pool contra fuera del pool ---
  const poolVs = document.createElement("div");
  poolVs.className = "col";
  poolVs.innerHTML = `<h3>Pool vs fuera del pool</h3><div class="barras-pool"><canvas id="grafica-pool"></canvas></div>`;
  container.appendChild(poolVs);
  const ctxPool = document.getElementById("grafica-pool").getContext("2d");
  const grupoFuera = csEnPool.find((g) => g.clave === "fuera");
  const datosPool = [
    { etiqueta: "En el pool", tasa: grupoPool ? grupoPool.tasa : 0, n: grupoPool ? grupoPool.partidas : 0 },
    { etiqueta: "Fuera del pool", tasa: grupoFuera ? grupoFuera.tasa : 0, n: grupoFuera ? grupoFuera.partidas : 0 },
  ];
  new Chart(ctxPool, {
    type: "bar",
    data: {
      labels: datosPool.map((d) => d.etiqueta),
      datasets: [
        {
          label: "Tasa de victorias",
          data: datosPool.map((d) => d.tasa),
          backgroundColor: ["var(--victoria)", "var(--texto-suave)"],
          borderWidth: 0,
          borderRadius: 4,
        },
      ],
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
              const d = datosPool[ctx.dataIndex];
              return `${d.tasa} % · ${d.n} partidas`;
            },
          },
        },
      },
      scales: {
        x: {
          min: 0,
          max: 100,
          grid: { color: "var(--borde)" },
          ticks: { color: "var(--texto-suave)", font: { size: 11 } },
          title: { display: true, text: "Tasa de victorias (%)", color: "var(--texto-suave)" },
        },
        y: {
          grid: { display: false },
          ticks: { color: "var(--texto)", font: { size: 12 } },
        },
      },
      animation: { duration: 0 },
    },
  });

  const leyenda = document.createElement("div");
  leyenda.className = "leyenda-pool suave";
  leyenda.textContent = datosPool
    .map((d) => `${d.etiqueta}: ${d.tasa} % · ${d.n} de ${partidas.length}`)
    .join("   ");
  poolVs.appendChild(leyenda);
}
