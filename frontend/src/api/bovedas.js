import { apiFetch, descargarArchivoPost, query } from './client.js'

export const listarBovedas = (filtros = {}) => apiFetch(`/bovedas${query(filtros)}`, { omitirManejador: true })
export const obtenerBoveda = (id) => apiFetch(`/bovedas/${id}`, { omitirManejador: true })
export const crearBoveda = (datos) => apiFetch('/bovedas', { method: 'POST', body: datos, omitirManejador: true })
export const desbloquearBoveda = (id, password) =>
  apiFetch(`/bovedas/${id}/desbloquear`, { method: 'POST', body: { password }, omitirManejador: true })
export const agregarEntrada = (id, datos) =>
  apiFetch(`/bovedas/${id}/entradas`, { method: 'POST', body: datos, omitirManejador: true })
export const cambiarCredenciales = (id, datos) =>
  apiFetch(`/bovedas/${id}/credenciales`, { method: 'PUT', body: datos, omitirManejador: true })
export const eliminarBoveda = (id) => apiFetch(`/bovedas/${id}`, { method: 'DELETE', omitirManejador: true })

// --- adjuntos (Fase 6, mejora M4.1) ---------------------------------------
// La contraseña viaja siempre en el **cuerpo** de la petición: nunca en la
// URL, donde acabaría en los registros del servidor y en el `Referer`.

/**
 * Sube un archivo al fondo que abre `password`.
 *
 * El backend decide sola qué vista es: la contraseña *es* la credencial del
 * fondo, así que el cliente nunca envía el identificador de la vista.
 */
export function adjuntarArchivo(id, { password, archivo, titulo = '' }) {
  const formulario = new FormData()
  formulario.append('password', password)
  formulario.append('titulo', titulo || '')
  formulario.append('archivo', archivo)
  return apiFetch(`/bovedas/${id}/adjuntos`, {
    method: 'POST',
    body: formulario,
    omitirManejador: true,
  })
}

/** Descarga un adjunto (el servidor re-verifica el SHA-256 antes de servirlo). */
export const descargarAdjunto = (id, adjuntoId, password, nombre) =>
  descargarArchivoPost(
    `/bovedas/${id}/adjuntos/${adjuntoId}/descargar`,
    nombre,
    { password },
    { omitirManejador: true },
  )

/** Re-verifica la integridad (SHA-256) de un adjunto. */
export const verificarAdjunto = (id, adjuntoId, password) =>
  apiFetch(`/bovedas/${id}/adjuntos/${adjuntoId}/verificar-integridad`, {
    method: 'POST',
    body: { password },
    omitirManejador: true,
  })

/**
 * Elimina un adjunto.
 *
 * Los bytes cifrados **permanecen** en el blob (el tamaño del archivo no debe
 * delatar cuántas descargas hubo) y el contador de nonces no se libera.
 */
export const eliminarAdjunto = (id, adjuntoId, password) =>
  apiFetch(`/bovedas/${id}/adjuntos/${adjuntoId}`, {
    method: 'DELETE',
    body: { password },
    omitirManejador: true,
  })

/** Migra una bóveda heredada (solo texto) al formato con adjuntos. */
export const modernizarBoveda = (id, datos) =>
  apiFetch(`/bovedas/${id}/modernizar`, { method: 'POST', body: datos, omitirManejador: true })
