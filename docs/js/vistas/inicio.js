/* Vista Inicio (sección 1b, T06 de PLAN.md).
   Recibe datos ya calculados y solo dibuja. */

import { agrupar, resumen, tendencia } from "../calc.js";

function cssVar(nombre) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(nombre)
    .trim();
}

function formatoNumero(valor, decimales = 1) {
  if (valor == null) return "—";
  return valor.toFixed(decimales);
}

function signo(valor) {
  if (valor == null) return "";
  return valor > 0 ? "+" + valor : valor;
}

function crearSparkline(canvas, valores, color) {
  const ctx = canvas.getContext("2d");
  const datosFiltrados = valores.map((v, i) => ({ x: i, y: v }));
  new Chart(ctx, {
    type: "line",
    data: {
      datasets: [
        {
          data: datosFiltrados,
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
      scales: {
        x: { display: false },
        y: { display: false },
      },
      animation: { duration: 0 },
    },
  });
}

function tarjetaIndicador(container, titulo, valor, comparte, partidas, valoresSpark, color) {
  const tarjeta = document.createElement("div");
  tarjeta.className = "tarjeta indicador";
  const canvas = document.createElement("canvas");
  canvas.className = "spark";
  canvas.width = 220;
  canvas.height = 44;
  tarjeta.innerHTML = `
    <div class="valor">${formatoNumero(valor)}</div>
    <div class="etiqueta">${titulo}</div>
    <div class="meta suave">${comparte}</div>
    <div class="partidas suave">${partidas} partida${partidas !== 1 ? "s" : ""}</div>
  `;
  tarjeta.appendChild(canvas);
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
  const tasaPool = grupoPool ? grupoPool.tasa : 0;
  const partidasPool = grupoPool ? grupoPool.partidas : 0;

  tarjetaIndicador(
    indicadores,
    "CS al minuto 10",
    res.cs10,
    `Meta ${perfil.meta_cs_10} · ${res.partidas} partidas`,
    res.partidas,
    sparkCs,
    cssVar("--victoria")
  );
  tarjetaIndicador(
    indicadores,
    "Oro al minuto 15",
    res.difOro15,
    `Por detrás en ${res.porDetras15} de ${res.conDato15}`,
    res.conDato15,
    sparkOro,
    res.difOro15 < 0 ? cssVar("--derrota") : cssVar("--victoria")
  );
  tarjetaIndicador(
    indicadores,
    "Muertes antes del 14",
    res.muertes14,
    `Meta ${perfil.meta_muertes_14} · ${res.partidas} partidas`,
    res.partidas,
    sparkMuertes,
    res.muertes14 > perfil.meta_muertes_14 ? cssVar("--derrota") : cssVar("--victoria")
  );
  tarjetaIndicador(
    indicadores,
    "Tasa dentro del pool",
    tasaPool,
    `${partidasPool} partidas`,
    partidasPool,
    [],
    cssVar("--acento")
  );

  // --- Gráfica de progreso: CS al 10 media móvil de 10 ---
  const progreso = document.createElement("div");
  progreso.className = "col";
  progreso.innerHTML = `<h3>Progreso CS al minuto 10</h3><canvas class="grafica" id="grafica-progreso"></canvas>`;
  container.appendChild(progreso);
  const ctxProgreso = document.getElementById("grafica-progreso").getContext("2d");
  const mediaMovil = tendencia(partidas, "cs_10", 10);
  const etiquetas = partidas.map((_p, i) => i + 1);
  new Chart(ctxProgreso, {
    type: "line",
    data: {
      labels: etiquetas,
      datasets: [
        {
          label: "CS al 10 (móvil 10)",
          data: mediaMovil,
          borderColor: cssVar("--texto"),
          backgroundColor: "rgba(230, 235, 245, 0.1)",
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.3,
        },
        {
          label: "Meta",
          data: etiquetas.map(() => perfil.meta_cs_10),
          borderColor: cssVar("--acento"),
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
        legend: { display: false, labels: { color: cssVar("--texto-suave") } },
        title: {
          display: true,
          text: "CS al minuto 10 vs meta",
          color: cssVar("--texto-suave"),
          font: { size: 13 },
        },
      },
      scales: {
        x: {
          display: partidas.length > 0,
          grid: { color: cssVar("--borde") },
          ticks: { color: cssVar("--texto-suave"), font: { size: 11 } },
          title: { display: true, text: "Partida", color: cssVar("--texto-suave") },
        },
        y: {
          grid: { color: cssVar("--borde") },
          ticks: { color: cssVar("--texto-suave"), font: { size: 11 } },
          title: {
            display: true,
            text: "CS",
            color: cssVar("--texto-suave"),
          },
        },
      },
      animation: { duration: 0 },
    },
  });

  // --- Pool contra fuera del pool ---
  const poolVs = document.createElement("div");
  poolVs.className = "col";
  poolVs.innerHTML = `<h3>Pool vs fuera del pool</h3><canvas class="grafica" id="grafica-pool"></canvas>`;
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
          backgroundColor: [
            cssVar("--victoria"),
            cssVar("--texto-suave"),
          ],
          borderWidth: 0,
          borderRadius: 6,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: "Tasa de victorias y nº de partidas",
          color: cssVar("--texto-suave"),
          font: { size: 13 },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const d = datosPool[ctx.dataIndex];
              return `${d.tasa}% · ${d.n} partidas`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: cssVar("--borde") },
          ticks: { color: cssVar("--texto-suave"), font: { size: 11 } },
          title: { display: true, text: "Tasa de victorias (%)", color: cssVar("--texto-suave") },
          max: 100,
        },
        y: {
          grid: { display: false },
          ticks: { color: cssVar("--texto"), font: { size: 12 } },
        },
      },
      animation: { duration: 0 },
    },
  });
}
