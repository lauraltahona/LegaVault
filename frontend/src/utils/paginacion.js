/**
 * Utilidades de paginación de listados (mejora #10 del plan).
 *
 * Los listados del backend devuelven ``{items, total, pagina, por_pagina,
 * paginas}``; los endpoints que aún no se paginaron devuelven un array plano.
 * ``itemsDe`` normaliza ambos formatos para que la interfaz no se rompa con
 * ninguno de los dos.
 */

export function itemsDe(respuesta, defecto = []) {
  if (Array.isArray(respuesta)) return respuesta
  if (respuesta && Array.isArray(respuesta.items)) return respuesta.items
  return defecto
}
