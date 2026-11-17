/* Vista Pool (sección 1b, T07 de PLAN.md).
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
  return valor > 0 ? "+" + valor : valor;
}

function claveGrupo(p) {
  return `${p.campeon}|${p.posicion}`;
}

function renderTarjeta(contenedor, grupo, version, escala, esReducida) {
  const { clave, partidas, victorias, tasa_ajustada, cs_10, dif_oro_15, muertes_14 } = grupo;
  const [campeon, posicion] = clave.split("|");
  const muestraPequena = partidas < 10;
  const oroEntero = Math.round(dif_oro_15 ?? 0);

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
      <div><span class="valor">${formatoNumero(tasa_ajustada)}%</span> tasa ajustada</div>
      <div><span class="valor">${formatoNumero(cs_10)}</span> CS al 10</div>
      <div><span class="valor oro">${numeroConSigno(oroEntero)}</span> oro al 15</div>
      <div><span class="valor">${formatoNumero(muertes_14, 2)}</span> muertes &lt; 14</div>
    </div>
    <div class="indicador-linea">
      <div class="barra-contenedor">
        <div class="cero"></div>
        <div class="barra" style="background:${dif_oro_15 >= 0 ? token("victoria") : token("derrota")}"></div>
        <span class="numero-linea">${numeroConSigno(oroEntero)}</span>
      </div>
    </div>
    ${muestraPequena ? '<span class="etiqueta muestra-pequena">muestra pequeña</span>' : ""}
  `;

  const barra = tarjeta.querySelector(".barra");
  const numero = tarjeta.querySelector(".numero-linea");
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
  if (dif_oro_15 == null) {
    barra.style.width = "0";
    numero.textContent = "—";
  } else {
    numero.textContent = numeroConSigno(oroEntero);
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

  const gruposPool = agrupar(enPool, claveGrupo);
  const gruposFuera = agrupar(fueraPool, claveGrupo);

  // Escala común para las barras de oro al 15 (mitad del ancho a cada lado del cero).
  const todos = [...gruposPool, ...gruposFuera];
  const escala = Math.max(1, ...todos.map((g) => Math.abs(g.dif_oro_15 ?? 0)));

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
    detalles.innerHTML = `<summary>Fuera del pool (${gruposFuera.length} combinación${gruposFuera.length !== 1 ? "s" : ""})</summary><div class='tarjetas'></div>`;
    const tarjetasFuera = detalles.querySelector(".tarjetas");
    for (const grupo of gruposFuera) {
      renderTarjeta(tarjetasFuera, grupo, version, escala, true);
    }
    container.appendChild(detalles);
  }
}
