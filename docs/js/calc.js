/* Funciones puras de cálculo para la página estática.
   Operan sobre los objetos del contrato (sección 3.2 de PLAN.md) que usan
   claves en snake_case (cs_10, dif_oro_15, muertes_14, victoria). */

export function tasaAjustada(victorias, partidas, prior = 10) {
  return 100 * (victorias + prior / 2) / (partidas + prior);
}

function promedio(valores) {
  if (valores.length === 0) return null;
  const suma = valores.reduce((acumulado, valor) => acumulado + valor, 0);
  return Math.round((suma / valores.length) * 10) / 10;
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
