/* Carga de datos: lee los seis JSON del contrato en paralelo, más referencias.json si existe. */

const ARCHIVOS = ["meta", "partidas", "curvas", "muertes", "compras", "estaticos"];

export async function cargarDatos() {
  const datos = {};
  const errores = [];

  await Promise.all(
    ARCHIVOS.map(async (nombre) => {
      try {
        const respuesta = await fetch(`data/${nombre}.json`, { cache: "no-cache" });
        if (!respuesta.ok) {
          throw new Error(`${nombre}.json: ${respuesta.status}`);
        }
        datos[nombre] = await respuesta.json();
      } catch (error) {
        errores.push(error.message);
      }
    })
  );

  // Opcional (fase 2): sin referencias la página funciona igual.
  datos.referencias = await cargarOpcional("referencias");

  if (errores.length > 0) {
    const evento = new CustomEvent("errorcargadatos", {
      detail: { archivos: errores.join(", ") },
    });
    window.dispatchEvent(evento);
    throw new Error(`No se pudieron cargar: ${errores.join(", ")}`);
  }

  return datos;
}

async function cargarOpcional(nombre) {
  try {
    const respuesta = await fetch(`data/${nombre}.json`, { cache: "no-cache" });
    return respuesta.ok ? await respuesta.json() : null;
  } catch (error) {
    return null;
  }
}
