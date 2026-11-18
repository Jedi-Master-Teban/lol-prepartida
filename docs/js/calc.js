/* Funciones puras de cálculo para la página estática.
   Operan sobre los objetos del contrato (sección 3.2 de PLAN.md) que usan
   claves en snake_case (cs_10, dif_oro_15, muertes_14, victoria). */

export function tasaAjustada(victorias, partidas, prior = 10) {
  return 100 * (victorias + prior / 2) / (partidas + prior);
}

function promedio(valores) {
  if (valores.length === 0) return null;
  const suma = valores.reduce((acumulado, valor) => acumulado + valor, 0);
  return suma / valores.length;
}

export function agrupar(partidas, fnClave) {
  const grupos = {};
  for (const p of partidas) {
    const clave = fnClave(p);
    if (!grupos[clave]) {
      grupos[clave] = {
        partidas: 0,
        victorias: 0,
        cs10: [],
        difOro15: [],
        muertes14: [],
      };
    }
    const g = grupos[clave];
    g.partidas += 1;
    if (p.victoria) g.victorias += 1;
    if (p.cs_10 != null) g.cs10.push(p.cs_10);
    if (p.dif_oro_15 != null) g.difOro15.push(p.dif_oro_15);
    if (p.muertes_14 != null) g.muertes14.push(p.muertes_14);
  }
  const salida = [];
  for (const [clave, g] of Object.entries(grupos)) {
    salida.push({
      clave,
      partidas: g.partidas,
      victorias: g.victorias,
      tasa: Math.round((100 * g.victorias) / g.partidas * 10) / 10,
      tasaAjustada: tasaAjustada(g.victorias, g.partidas),
      cs10: promedio(g.cs10),
      difOro15: promedio(g.difOro15),
      muertes14: promedio(g.muertes14),
    });
  }
  return salida;
}

export function resumen(partidas) {
  const n = partidas.length;
  const victorias = partidas.filter((p) => p.victoria).length;
  const conDato15 = partidas.filter((p) => p.dif_oro_15 != null).length;
  const porDetras15 = partidas.filter(
    (p) => p.dif_oro_15 != null && p.dif_oro_15 < 0
  ).length;
  return {
    partidas: n,
    victorias,
    derrotas: n - victorias,
    tasa: n ? Math.round((100 * victorias) / n * 10) / 10 : 0,
    tasaAjustada: tasaAjustada(victorias, n),
    cs10: promedio(partidas.map((p) => p.cs_10).filter((v) => v != null)),
    difOro15: promedio(
      partidas.map((p) => p.dif_oro_15).filter((v) => v != null)
    ),
    muertes14: promedio(partidas.map((p) => p.muertes_14)),
    porDetras15,
    conDato15,
  };
}

export function tendencia(partidas, campo, ventana = 10) {
  const resultado = [];
  for (let i = 0; i < partidas.length; i++) {
    const inicio = Math.max(0, i - ventana + 1);
    const valores = partidas
      .slice(inicio, i + 1)
      .map((p) => p[campo])
      .filter((v) => v != null);
    resultado.push(promedio(valores));
  }
  return resultado;
}

export function curvaPromedio(curvas, ids, campo, hastaMinuto = 20) {
  const resultado = [];
  for (let minuto = 0; minuto <= hastaMinuto; minuto++) {
    const valores = [];
    for (const id of ids) {
      const serie = curvas[id];
      if (serie && Array.isArray(serie[campo]) && minuto < serie[campo].length) {
        const valor = serie[campo][minuto];
        if (valor != null) valores.push(valor);
      }
    }
    resultado.push(valores.length ? promedio(valores) : null);
  }
  return resultado;
}

export function partidasDeHoy(partidas, perfil, ahora) {
  const referencia = new Date(ahora.getTime() - perfil.desfase_horas * 3600 * 1000);
  const dia = referencia.toISOString().slice(0, 10);
  return partidas.filter((p) => p.dia_sesion === dia);
}

export function aCoordenadaMapa(x, y) {
  return {
    izquierda: (x / 14870) * 100,
    arriba: (1 - y / 14980) * 100,
  };
}

/* --- Referencias por rango (R05, sección 3.8 de PLAN.md) --- */

/* Métricas comparables, en el orden en que se muestran.
   mayorEsMejor: true si un valor más alto es mejor. */
export const METRICAS_REFERENCIA = [
  { clave: "cs_10", titulo: "CS al minuto 10", mayorEsMejor: true, decimales: 1 },
  { clave: "dif_oro_15", titulo: "Oro al minuto 15", mayorEsMejor: true, decimales: 0 },
  { clave: "muertes_14", titulo: "Muertes antes del 14", mayorEsMejor: false, decimales: 2 },
];

export function rolDeReferencia(perfil) {
  return (perfil && perfil.rol_principal) || "MIDDLE";
}

/* Promedios del jugador solo en las partidas del rol, para compararlos con la referencia del mismo rol. */
export function valoresDelRol(partidas, rol) {
  const delRol = partidas.filter((p) => p.posicion === rol);
  const media = (campo) => promedio(delRol.map((p) => p[campo]).filter((v) => v != null));
  return {
    partidas: delRol.length,
    cs_10: media("cs_10"),
    dif_oro_15: media("dif_oro_15"),
    muertes_14: media("muertes_14"),
  };
}

/* Distancia a la mediana medida en rangos intercuartílicos (p75 − p25).
   Positiva = desfavorable para el jugador. */
export function brechaIqr(valor, percentiles, mayorEsMejor) {
  if (valor == null || !percentiles || percentiles.p50 == null) return null;
  const iqr = percentiles.p75 - percentiles.p25;
  if (!iqr) return null;
  const diferencia = mayorEsMejor ? percentiles.p50 - valor : valor - percentiles.p50;
  return diferencia / iqr;
}

/* La métrica con la mayor brecha desfavorable; null si ninguna es desfavorable. */
export function mayorBrecha(valores, referenciaRol) {
  let mejor = null;
  for (const m of METRICAS_REFERENCIA) {
    const b = brechaIqr(valores[m.clave], referenciaRol[m.clave], m.mayorEsMejor);
    if (b != null && b > 0 && (mejor == null || b > mejor.brecha)) {
      mejor = { metrica: m.clave, brecha: b };
    }
  }
  return mejor;
}

export function textoDistancia(valor, mediana, mayorEsMejor, decimales) {
  const diferencia = valor - mediana;
  const abs = Math.abs(diferencia).toFixed(decimales);
  if (Number(abs) === 0) return "en la mediana";
  const peor = mayorEsMejor ? diferencia < 0 : diferencia > 0;
  if (mayorEsMejor) return peor ? `te faltan ${abs}` : `le sacas ${abs}`;
  return peor ? `te sobran ${abs}` : `tienes ${abs} menos`;
}

/* Posición horizontal (0–100 %) de un valor en una regla de minimo a maximo. */
export function posicionEnRegla(valor, minimo, maximo) {
  if (maximo === minimo) return 50;
  const pct = ((valor - minimo) / (maximo - minimo)) * 100;
  return Math.max(0, Math.min(100, pct));
}
