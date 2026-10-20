/** Utilidades de formato para la interfaz. */

export function fechaHora(valor) {
  if (!valor) return '—'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return '—'
  return fecha.toLocaleString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function fecha(valor) {
  if (!valor) return '—'
  const fechaObj = new Date(valor)
  if (Number.isNaN(fechaObj.getTime())) return '—'
  return fechaObj.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function tamanoArchivo(bytes) {
  if (!bytes && bytes !== 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function etiqueta(mapa, clave) {
  return mapa?.[clave] ?? clave ?? '—'
}

/**
 * Hash truncado para mostrar en tablas y cadenas: `abcdef12…`.
 * Con `cola > 0` también se muestran los últimos caracteres
 * (`abcdef12…12ab34`), útil para la cadena de auditoría donde se
 * quiere ver que el hash de un eslabón es el «hash anterior» del siguiente.
 */
export function hashCorto(hash, cabeza = 10, cola = 0) {
  if (!hash) return '—'
  const inicio = hash.slice(0, cabeza)
  const final = cola > 0 ? hash.slice(-cola) : ''
  return final ? `${inicio}…${final}` : `${inicio}…`
}
