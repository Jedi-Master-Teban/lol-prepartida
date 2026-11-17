import { describe, test } from "node:test";
import assert from "node:assert";
import {
  tasaAjustada,
  agrupar,
  resumen,
  tendencia,
  curvaPromedio,
  partidasDeHoy,
  aCoordenadaMapa,
} from "./calc.js";

describe("tasaAjustada", () => {
  test("contrae hacia el 50 % con prior de 10", () => {
    assert.strictEqual(Math.round(tasaAjustada(2, 3) * 10) / 10, 53.8);
  });
  test("sin partidas da 50", () => {
    assert.strictEqual(tasaAjustada(0, 0), 50);
  });
  test("100 % de victorias con prior", () => {
    assert.strictEqual(Math.round(tasaAjustada(10, 10) * 10) / 10, 75);
  });
});

describe("agrupar", () => {
  const partidas = [
    { victoria: true, cs_10: 70, dif_oro_15: 100, muertes_14: 0 },
    { victoria: true, cs_10: 80, dif_oro_15: 200, muertes_14: 1 },
    { victoria: false, cs_10: 60, dif_oro_15: null, muertes_14: 3 },
  ];

  test("tasa de victorias del grupo", () => {
    const grupos = agrupar(partidas, () => "mismo");
    assert.strictEqual(grupos.length, 1);
    assert.strictEqual(grupos[0].partidas, 3);
    assert.strictEqual(grupos[0].victorias, 2);
    assert.strictEqual(grupos[0].tasa, 66.7);
  });

  test("los promedios ignoran null", () => {
    const grupos = agrupar(partidas, () => "mismo");
    assert.strictEqual(grupos[0].cs10, 70);
    assert.strictEqual(grupos[0].difOro15, 150);
    assert.ok(Math.abs(grupos[0].muertes14 - 1.33) < 0.01);
  });

  test("agrupa por clave de función", () => {
    const grupos = agrupar(partidas, (p) => (p.victoria ? "victoria" : "derrota"));
    assert.strictEqual(grupos.length, 2);
    const victoria = grupos.find((g) => g.clave === "victoria");
    const derrota = grupos.find((g) => g.clave === "derrota");
    assert.strictEqual(victoria.partidas, 2);
    assert.strictEqual(derrota.partidas, 1);
  });

  test("array vacío devuelve array vacío", () => {
    assert.deepStrictEqual(agrupar([], () => "x"), []);
  });
});

describe("resumen", () => {
  const partidas = [
    { victoria: true, cs_10: 70, dif_oro_15: 100, muertes_14: 0 },
    { victoria: false, cs_10: 80, dif_oro_15: -50, muertes_14: 2 },
    { victoria: true, cs_10: null, dif_oro_15: null, muertes_14: 1 },
  ];

  test("totales y promedios generales", () => {
    const r = resumen(partidas);
    assert.strictEqual(r.partidas, 3);
    assert.strictEqual(r.victorias, 2);
    assert.strictEqual(r.derrotas, 1);
    assert.strictEqual(r.tasa, 66.7);
    assert.strictEqual(r.cs10, 75);
    assert.strictEqual(r.difOro15, 25);
    assert.strictEqual(r.muertes14, 1);
  });

  test("porDetras15 y conDato15", () => {
    const r = resumen(partidas);
    assert.strictEqual(r.conDato15, 2);
    assert.strictEqual(r.porDetras15, 1);
  });

  test("array vacío", () => {
    const r = resumen([]);
    assert.strictEqual(r.partidas, 0);
    assert.strictEqual(r.victorias, 0);
    assert.strictEqual(r.tasa, 0);
    assert.strictEqual(r.cs10, null);
  });
});

describe("tendencia", () => {
  const partidas = [
    { cs_10: 10 }, { cs_10: 20 }, { cs_10: 30 }, { cs_10: 40 }, { cs_10: 50 },
    { cs_10: null }, { cs_10: 70 },
  ];

  test("media móvil ignorando null", () => {
    const t = tendencia(partidas, "cs_10", 3);
    assert.strictEqual(t.length, 7);
    assert.strictEqual(t[0], 10);
    assert.strictEqual(t[1], 15);
    assert.strictEqual(t[2], 20);
    assert.strictEqual(t[5], 45); // (40 + 50 + null) / 2
    assert.strictEqual(t[6], 60); // (50 + null + 70) / 2
  });
});

describe("curvaPromedio", () => {
  const curvas = {
    A: { oro: [100, 200, 300], cs: [0, 5, 10], dif_oro: [0, 10, 20] },
    B: { oro: [150, null, 350], cs: [2, 7, 12], dif_oro: [0, null, 25] },
  };

  test("promedio por minuto entre partidas", () => {
    const c = curvaPromedio(curvas, ["A", "B"], "oro", 2);
    assert.deepStrictEqual(c, [125, 200, 325]);
  });

  test("hastaMinuto limita el rango", () => {
    const c = curvaPromedio(curvas, ["A"], "cs", 1);
    assert.deepStrictEqual(c, [0, 5]);
  });
});

describe("partidasDeHoy", () => {
  const partidas = [
    { dia_sesion: "2026-11-16", campeon: "Ahri" },
    { dia_sesion: "2026-11-15", campeon: "Sylas" },
  ];
  const perfil = { desfase_horas: 10 };

  test("filtra por dia de sesion", () => {
    const ahora = new Date(Date.UTC(2026, 10, 16, 12, 0, 0)); // 16 nov 12:00 UTC
    const hoy = partidasDeHoy(partidas, perfil, ahora);
    assert.strictEqual(hoy.length, 1);
    assert.strictEqual(hoy[0].campeon, "Ahri");
  });
});

describe("aCoordenadaMapa", () => {
  test("origen abajo a la izquierda", () => {
    assert.deepStrictEqual(aCoordenadaMapa(0, 0), { izquierda: 0, arriba: 100 });
  });
  test("esquina opuesta", () => {
    const c = aCoordenadaMapa(14870, 14980);
    assert.strictEqual(c.izquierda, 100);
    assert.strictEqual(c.arriba, 0);
  });
});
