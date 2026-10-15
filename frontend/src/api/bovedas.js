import { apiFetch, query } from './client.js'

export const listarBovedas = (filtros = {}) => apiFetch(`/bovedas${query(filtros)}`)

export const obtenerBoveda = (id) => apiFetch(`/bovedas/${id}`)

export const crearBoveda = (datos) => apiFetch('/bovedas', { method: 'POST', body: datos })

export const desbloquearBoveda = (id, password) =>
  apiFetch(`/bovedas/${id}/desbloquear`, { method: 'POST', body: { password } })

export const agregarEntrada = (id, datos) =>
  apiFetch(`/bovedas/${id}/entradas`, { method: 'POST', body: datos })

export const cambiarCredenciales = (id, datos) =>
  apiFetch(`/bovedas/${id}/credenciales`, { method: 'PUT', body: datos })

export const eliminarBoveda = (id) => apiFetch(`/bovedas/${id}`, { method: 'DELETE' })
