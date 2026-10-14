import { apiFetch, descargarArchivo, query } from './client.js'

export const listarDocumentos = (filtros = {}) => apiFetch(`/documentos${query(filtros)}`)

export const obtenerDocumento = (id) => apiFetch(`/documentos/${id}`)

export function cargarDocumento(expedienteId, tipo, nivelSensibilidad, descripcion, archivo) {
  const formulario = new FormData()
  formulario.append('expediente_id', expedienteId)
  formulario.append('tipo', tipo)
  formulario.append('nivel_sensibilidad', nivelSensibilidad)
  formulario.append('descripcion', descripcion || '')
  formulario.append('archivo', archivo)
  return apiFetch('/documentos', { method: 'POST', body: formulario })
}

export const eliminarDocumento = (id) => apiFetch(`/documentos/${id}`, { method: 'DELETE' })

export const descargarDocumento = (id, nombre) =>
  descargarArchivo(`/documentos/${id}/descargar`, nombre)
