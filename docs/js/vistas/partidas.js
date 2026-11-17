/* Vista Partidas (sección 1b, T10b de PLAN.md).
   Recibe datos ya calculados y solo dibuja. */

import { curvaPromedio } from "../calc.js";
import {
  urlCampeonRetrato,
  urlItem,
  urlHechizo,
  urlIcono,
} from "../imagenes.js";
import { token } from "../tema.js";

function formatoNumero(valor, decimales = 1) {
  if (valor == null) return "—";
  return valor.toFixed(decimales);
}

function numeroConSigno(valor) {
  if (valor == null) return "—";
  return valor > 0 ? "+" + valor : String(valor).replace("-", "\u2212");
}

function fechaLocal(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function horaLocal(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function nombreCampeonVisible(clave, estaticos) {
  if (!estaticos || !estaticos.campeones) return clave;
  for (const [id, info] of Object.entries(estaticos.campeones)) {
    if (info.clave === clave) return info.nombre || clave;
  }
  return clave;
}

function nombreHechizo(id, estaticos) {
  if (!estaticos || !estaticos.hechizos) return String(id);
  for (const [key, info] of Object.entries(estaticos.hechizos)) {
    if (String(key) === String(id)) return info.nombre || String(id);
  }
  return String(id);
}

function claveHechizo(id, estaticos) {
  if (!estaticos || !estaticos.hechizos) return String(id);
  for (const [key, info] of Object.entries(estaticos.hechizos)) {
    if (String(key) === String(id)) return info.clave || String(id);
  }
  return String(id);
}

function nombreRuna(id, estaticos) {
  if (!estaticos || !estaticos.runas) return String(id);
  const info = estaticos.runas[String(id)];
  return info ? info.nombre : String(id);
}

function iconoRuna(id, estaticos) {
  if (!estaticos || !estaticos.runas) return "";
  const info = estaticos.runas[String(id)];
  return info ? info.icono : "";
}

export function render(container, datos) {
  const { partidas, curvas, compras, meta, estaticos } = datos;
  const version = meta.version_ddragon;
  container.innerHTML = "";

  // Últimas 30 partidas, más reciente primero
  const recientes = [...partidas].reverse().slice(0, 30);

  // Tabla envuelta en contenedor con scroll horizontal
  const tablaWrap = document.createElement("div");
  tablaWrap.className = "tabla-wrap";
  const tabla = document.createElement("table");
  tabla.className = "tabla-partidas";
  tabla.innerHTML = `
    <thead>
      <tr>
        <th>Fecha</th>
        <th>Resultado</th>
        <th>Tú</th>
        <th>Rival</th>
        <th>Pos.</th>
        <th>Lado</th>
        <th>KDA</th>
        <th>CS@10</th>
        <th>Oro@15</th>
        <th>Muertes&lt;14</th>
        <th>Hechizos</th>
        <th>Runa</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = tabla.querySelector("tbody");
  tablaWrap.appendChild(tabla);
  container.appendChild(tablaWrap);

  // Fila de detalle (oculta por defecto)
  const filaDetalle = document.createElement("tr");
  filaDetalle.className = "fila-detalle";
  filaDetalle.style.display = "none";
  const tdDetalle = document.createElement("td");
  tdDetalle.colSpan = 12;
  tdDetalle.className = "td-detalle";
  filaDetalle.appendChild(tdDetalle);
  tbody.parentNode.insertBefore(filaDetalle, tbody.nextSibling);

  let filaAbierta = null;
let chartOroDetalle = null;
let chartCsDetalle = null;

  function destruirGraficasDetalle() {
    if (chartOroDetalle) { chartOroDetalle.destroy(); chartOroDetalle = null; }
    if (chartCsDetalle) { chartCsDetalle.destroy(); chartCsDetalle = null; }
  }

  function construirFila(p) {
    const tr = document.createElement("tr");
    tr.className = "fila-partida";
    tr.dataset.matchId = p.match_id;
    const v = p.victoria;
    const resultadoTexto = v ? "Victoria" : "Derrota";
    const resultadoColor = v ? token("victoria") : token("derrota");

    const propioClave = p.campeon;
    const rivalClave = p.rival || "—";
    const propioNombre = nombreCampeonVisible(propioClave, estaticos);
    const rivalNombre = nombreCampeonVisible(rivalClave, estaticos);

    const imgPropio = urlCampeonRetrato(propioClave, version);
    const imgRival = rivalClave !== "—" ? urlCampeonRetrato(rivalClave, version) : "";

    const kda = `${p.asesinatos}/${p.muertes}/${p.asistencias}`;

    // Hechizos
    const h1 = p.hechizos && p.hechizos[0] != null ? p.hechizos[0] : null;
    const h2 = p.hechizos && p.hechizos[1] != null ? p.hechizos[1] : null;
    const imgH1 = h1 != null ? urlHechizo(claveHechizo(h1, estaticos), version) : "";
    const imgH2 = h2 != null ? urlHechizo(claveHechizo(h2, estaticos), version) : "";

    // Runa
    const runaId = p.runa_clave;
    const runaNombre = nombreRuna(runaId, estaticos);
    const runaIcono = iconoRuna(runaId, estaticos);
    const imgRuna = runaIcono ? urlIcono(runaIcono) : "";

    tr.innerHTML = `
      <td>${fechaLocal(p.inicio)} ${horaLocal(p.inicio)}</td>
      <td style="color:${resultadoColor};font-weight:700">${resultadoTexto}</td>
      <td><div class="celda-con-icono"><img src="${imgPropio}" alt="${propioNombre}" class="icono-pequeno" onerror="this.style.display='none';this.nextElementSibling.textContent='${propioNombre}';"><span class="nombre-pequeno">${propioNombre}</span></div></td>
      <td><div class="celda-con-icono">${imgRival ? `<img src="${imgRival}" alt="${rivalNombre}" class="icono-pequeno" onerror="this.style.display='none';this.nextElementSibling.textContent='${rivalNombre}';"><span class="nombre-pequeno">${rivalNombre}</span>` : "<span>—</span>"}</div></td>
      <td>${p.posicion || "—"}</td>
      <td>${p.lado || "—"}</td>
      <td>${kda}</td>
      <td>${formatoNumero(p.cs_10)}</td>
      <td>${numeroConSigno(p.dif_oro_15)}</td>
      <td>${p.muertes_14 != null ? p.muertes_14 : "—"}</td>
      <td class="celda-iconos">
        ${h1 != null ? `<img src="${imgH1}" alt="${nombreHechizo(h1, estaticos)}" class="icono-hechizo" onerror="this.style.display='none';this.nextElementSibling.textContent='${nombreHechizo(h1, estaticos)}';"><span class="nombre-hechizo">${nombreHechizo(h1, estaticos)}</span>` : "<span>—</span>"}
        ${h2 != null ? `<img src="${imgH2}" alt="${nombreHechizo(h2, estaticos)}" class="icono-hechizo" onerror="this.style.display='none';this.nextElementSibling.textContent='${nombreHechizo(h2, estaticos)}';"><span class="nombre-hechizo">${nombreHechizo(h2, estaticos)}</span>` : "<span>—</span>"}
      </td>
      <td class="celda-runa">
        ${runaId != null ? `<img src="${imgRuna}" alt="${runaNombre}" class="icono-runa" onerror="this.style.display='none';this.nextElementSibling.textContent='${runaNombre}';"><span class="nombre-runa">${runaNombre}</span>` : "<span>—</span>"}
      </td>
    `;

    tr.addEventListener("click", () => abrirDetalle(tr, p));

    return tr;
  }

  for (const p of recientes) {
    tbody.appendChild(construirFila(p));
  }

  function abrirDetalle(trFila, p) {
    // Destruir gráficas previas para evitar fugas de memoria
    destruirGraficasDetalle();

    // Marcar fila abierta
    if (filaAbierta) {
      filaAbierta.classList.remove("abierta");
    }
    filaAbierta = trFila;
    trFila.classList.add("abierta");

    // Construir contenido del detalle
    tdDetalle.innerHTML = "";

    const cerrar = document.createElement("button");
    cerrar.textContent = "×";
    cerrar.className = "cerrar-detalle";
    cerrar.addEventListener("click", (e) => {
      e.stopPropagation();
      cerrarDetalle();
    });
    tdDetalle.appendChild(cerrar);

    // Info de la partida
    const info = document.createElement("div");
    info.className = "info-partida";
    const v = p.victoria;
    info.innerHTML = `
      <div><strong>${p.campeon}</strong> vs <strong>${p.rival || "—"}</strong> · ${p.posicion || "—"} · ${p.lado || "—"}</div>
      <div>${fechaLocal(p.inicio)} ${horaLocal(p.inicio)} · ${v ? "Victoria" : "Derrota"} · KDA ${p.asesinatos}/${p.muertes}/${p.asistencias} · CS@10 ${formatoNumero(p.cs_10)} · Oro@15 ${numeroConSigno(p.dif_oro_15)} · Muertes&lt;14 ${p.muertes_14 != null ? p.muertes_14 : "—"}</div>
    `;
    tdDetalle.appendChild(info);

    // Gráficas
    const graficas = document.createElement("div");
    graficas.className = "graficas fila";
    tdDetalle.appendChild(graficas);

    // Chart 1: Diferencia de oro por minuto
    const colOro = document.createElement("div");
    colOro.className = "col";
    colOro.innerHTML = `<h3>Diferencia de oro por minuto</h3><div class="grafica"><canvas id="grafica-oro-detalle"></canvas></div>`;
    graficas.appendChild(colOro);

    // Chart 2: CS contra meta
    const colCs = document.createElement("div");
    colCs.className = "col";
    colCs.innerHTML = `<h3>CS contra la meta</h3><div class="grafica"><canvas id="grafica-cs-detalle"></canvas></div>`;
    graficas.appendChild(colCs);

    // Chart 3: Línea de tiempo de compras - HTML en vez de Chart.js
    const colCompras = document.createElement("div");
    colCompras.className = "col";
    tdDetalle.appendChild(colCompras);
    const comprasPartida = compras[p.match_id] || [];
    if (comprasPartida.length === 0) {
      colCompras.innerHTML = `<h3>Compras</h3><div class="compras-vacias">Sin compras de ítems completos registradas</div>`;
    } else {
      colCompras.innerHTML = `<h3>Compras</h3><div class="compras-timeline"></div>`;
      const timeline = colCompras.querySelector(".compras-timeline");
      comprasPartida.sort((a, b) => a.minuto - b.minuto);
      for (const c of comprasPartida) {
        const itemInfo = estaticos.items && estaticos.items[String(c.item_id)];
        const nombre = itemInfo ? itemInfo.nombre : `Ítem ${c.item_id}`;
        const itemUrl = urlItem(c.item_id, version);
        const compra = document.createElement("div");
        compra.className = "compra-item";
        compra.title = `${nombre}`;
        compra.innerHTML = `
          <img src="${itemUrl}" alt="${nombre}" class="icono-compra" onerror="this.style.display='none';this.nextElementSibling.textContent='${nombre}';">
          <div class="compra-minuto">${c.minuto.toFixed(1)} min</div>
        `;
        timeline.appendChild(compra);
      }
    }

    // Detalle justo debajo de la fila pulsada (corrección del supervisor, T10b)
    trFila.after(filaDetalle);
    filaDetalle.style.display = "table-row";
    filaDetalle.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // --- Chart 1: Diferencia de oro por minuto ---
    const ids = [p.match_id];
    const difOro = curvaPromedio(curvas, ids, "dif_oro", 20);
    const difPos = difOro.map((v) => (v != null && v > 0 ? v : 0));
    const difNeg = difOro.map((v) => (v != null && v < 0 ? v : 0));
    const difLine = difOro.map((v) => (v != null ? v : null));

    const ctxOro = document.getElementById("grafica-oro-detalle").getContext("2d");
    chartOroDetalle = new Chart(ctxOro, {
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
            showInLegend: false,
          },
          {
            label: "En contra",
            data: difNeg,
            backgroundColor: token("derrota"),
            borderWidth: 0,
            pointRadius: 0,
            fill: "origin",
            showInLegend: false,
          },
          {
            label: "Oro vs rival",
            data: difLine,
            borderColor: token("texto"),
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.15,
          },
          {
            label: "Cero",
            data: difOro.map(() => 0),
            borderColor: token("borde"),
            borderDash: [6, 4],
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            showInLegend: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, title: { display: false } },
        scales: {
          x: {
            type: "linear",
            title: { display: true, text: "Minuto", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
            min: 0,
            max: 20,
          },
          y: {
            title: { display: true, text: "Diferencia de oro", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
          },
        },
        animation: { duration: 0 },
      },
    });

    // --- Chart 2: CS acumulado contra meta ---
    const cs = curvaPromedio(curvas, ids, "cs", 20);
    const metaCs10 = meta.perfil.meta_cs_10;
    const pendiente = metaCs10 / 10;
    const metaLine = cs.map((_, i) => i * pendiente);

    const ctxCs = document.getElementById("grafica-cs-detalle").getContext("2d");
    chartCsDetalle = new Chart(ctxCs, {
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
            tension: 0.15,
          },
          {
            label: `Meta ${metaCs10}`,
            data: metaLine,
            borderColor: token("acento"),
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
          legend: { display: true, labels: { color: token("texto-suave"), font: { size: 12 } } },
          title: { display: false },
        },
        scales: {
          x: {
            type: "linear",
            title: { display: true, text: "Minuto", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
            min: 0,
            max: 20,
          },
          y: {
            title: { display: true, text: "CS acumulado", color: token("texto-suave") },
            ticks: { color: token("texto-suave"), font: { size: 11 } },
            grid: { color: token("borde") },
            beginAtZero: true,
          },
        },
        animation: { duration: 0 },
      },
    });
  }

  function cerrarDetalle() {
    if (filaAbierta) {
      filaAbierta.classList.remove("abierta");
      filaAbierta = null;
    }
    filaDetalle.style.display = "none";
  }
}
