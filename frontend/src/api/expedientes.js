import { apiFetch, query } from './client.js'

export const listarExpedientes = (filtros = {}) => apiFetch(`/expedientes${query(filtros)}`)

export const obtenerExpediente = (id) => apiFetch(`/expedientes/${id}`)

export const crearExpediente = (datos) => apiFetch('/expedientes', { method: 'POST', body: datos })

export const actualizarExpediente = (id, datos) =>
  apiFetch(`/expedientes/${id}`, { method: 'PUT', body: datos })

export const archivarExpediente = (id) => apiFetch(`/expedientes/${id}/archivar`, { method: 'PATCH' })
