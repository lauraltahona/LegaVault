import { apiFetch, query } from './client.js'

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
