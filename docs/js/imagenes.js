/* Funciones de URL de imágenes (sección 3.7 del contrato de datos) */

const DDRAWN_BASE = "https://ddragon.leagueoflegends.com";

export function versionBase() {
  return DDRAWN_BASE;
}

export function urlCampeonRetrato(clave, version) {
  return `${DDRAWN_BASE}/cdn/${version}/img/champion/${clave}.png`;
}

export function urlCampeonSplash(clave) {
  return `${DDRAWN_BASE}/cdn/img/champion/splash/${clave}_0.jpg`;
}

export function urlItem(itemId, version) {
  return `${DDRAWN_BASE}/cdn/${version}/img/item/${itemId}.png`;
}

export function urlHechizo(clave, version) {
  return `${DDRAWN_BASE}/cdn/${version}/img/spell/${clave}.png`;
}

export function urlIcono(icono) {
  return `${DDRAWN_BASE}/cdn/img/${icono}`;
}

export function urlMinimapa(version) {
  return `${DDRAWN_BASE}/cdn/${version}/img/map/map11.png`;
}
