/* Vista Pool (sección 1b, T07b de PLAN.md).
   Recibe datos ya calculados y solo dibuja. */

import { agrupar } from "../calc.js";
import { urlCampeonRetrato } from "../imagenes.js";
import { token } from "../tema.js";

function formatoNumero(valor, decimales = 1) {
  if (valor == null) return "—";
  return valor.toFixed(decimales);
}

function numeroConSigno(valor) {
  if (valor == null) return "—";
  return valor > 0 ? "+" + valor : String(valor).replace("-", "\u2212");
}

function claveGrupo(p) {
  return `${p.campeon}|${p.posicion}`;
}

function renderTarjeta(contenedor, grupo, version, escala, esReducida) {
  const {
    clave,
    partidas,
    victorias,
    tasaAjustada,
    cs10,
    difOro15,
    muertes14,
  } = grupo;
  const [campeon, posicion] = clave.split("|");
  const muestraPequena = partidas < 10;
  const oroEntero = difOro15 == null ? null : Math.round(difOro15);

  const tarjeta = document.createElement("article");
  tarjeta.className = `tarjeta tarjeta-campeon${esReducida ? " tarjeta-reducida" : ""}`;
  tarjeta.innerHTML = `
    <div class="cabecera-tarjeta">
      <img class="retrato${esReducida ? " reducida" : ""}" src="${urlCampeonRetrato(campeon, version)}" alt="${campeon}">
      <div class="identidad">
        <div class="nombre">${campeon}</div>
        <div class="posicion">${posicion}</div>
      </div>
    </div>
    <div class="estadisticas">
      <div><span class="valor">${partidas}</span> partidas</div>
      <div><span class="valor">${victorias}</span> victorias</div>
      <div><span class="valor">${formatoNumero(tasaAjustada)} %</span> tasa ajustada</div>
      <div><span class="valor">${formatoNumero(cs10)}</span> CS al 10</div>
      <div><span class="valor oro">${oroEntero == null ? "—" : numeroConSigno(oroEntero)}</span> oro al 15</div>
      <div><span class="valor">${formatoNumero(muertes14, 2)}</span> muertes &lt; 14</div>
    </div>
    <div class="indicador-linea">
      <div class="barra-contenedor">
        <div class="cero"></div>
        <div class="barra" style="background:${oroEntero != null && oroEntero >= 0 ? token("victoria") : token("derrota")}"></div>
        <span class="numero-linea">${oroEntero == null ? "—" : numeroConSigno(oroEntero)}</span>
      </div>
    </div>
    ${muestraPequena ? '<span class="etiqueta muestra-pequena">muestra pequeña</span>' : ""}
  `;

  const barra = tarjeta.querySelector(".barra");
  const numero = tarjeta.querySelector(".numero-linea");
  if (oroEntero == null) {
    barra.style.width = "0";
  } else {
    const pct = escala > 0 ? Math.min((Math.abs(oroEntero) / escala) * 50, 50) : 0;
    if (oroEntero >= 0) {
      barra.style.left = "50%";
      barra.style.width = `${pct}%`;
      numero.style.marginLeft = "8px";
      numero.style.marginRight = "";
    } else {
      barra.style.left = `${50 - pct}%`;
      barra.style.width = `${pct}%`;
      numero.style.marginRight = "8px";
      numero.style.marginLeft = "";
    }
  }

  contenedor.appendChild(tarjeta);
  return tarjeta;
}

export function render(container, datos) {
  const { partidas, meta } = datos;
  const version = meta.version_ddragon;
  container.innerHTML = "";

  const enPool = partidas.filter((p) => p.en_pool);
  const fueraPool = partidas.filter((p) => !p.en_pool);

  const gruposPool = agrupar(enPool, claveGrupo).sort((a, b) => b.partidas - a.partidas);
  const gruposFuera = agrupar(fueraPool, claveGrupo).sort((a, b) => b.partidas - a.partidas);

  // Escala común para las barras de oro al 15 (mitad del ancho a cada lado del cero).
  const todos = [...gruposPool, ...gruposFuera];
  const escala = Math.max(1, ...todos.map((g) => Math.abs(g.difOro15 ?? 0)));

  // --- En el pool ---
  const seccionPool = document.createElement("div");
  seccionPool.className = "seccion-pool";
  seccionPool.innerHTML = "<h3>En el pool</h3><div class='tarjetas'></div>";
  const tarjetasPool = seccionPool.querySelector(".tarjetas");
  for (const grupo of gruposPool) {
    renderTarjeta(tarjetasPool, grupo, version, escala, false);
  }
  container.appendChild(seccionPool);

  // --- Fuera del pool (plegable) ---
  if (gruposFuera.length > 0) {
    const detalles = document.createElement("details");
    detalles.className = "seccion-fuera";
    detalles.innerHTML = `<summary>Fuera del pool (${gruposFuera.length} combinaciones)</summary><div class='tarjetas'></div>`;
    const tarjetasFuera = detalles.querySelector(".tarjetas");
    for (const grupo of gruposFuera) {
      renderTarjeta(tarjetasFuera, grupo, version, escala, true);
    }
    container.appendChild(detalles);
  }
}
