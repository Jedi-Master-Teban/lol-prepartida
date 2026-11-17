/* Tokens de color resueltos de CSS para Chart.js.
   Chart.js no resuelve cadenas "var(--...)", así que se leen los valores
   computados de la hoja de estilos (sección 4 de PLAN.md). */

export function token(nombre) {
  return getComputedStyle(document.documentElement).getPropertyValue("--" + nombre).trim();
}
