import { apiFetch, query } from './client.js'

export const listarAlertas = (filtros = {}) => apiFetch(`/alertas${query(filtros)}`)

export const resumenAlertas = () => apiFetch('/alertas/resumen')

export const marcarAlertaLeida = (id, leida = true) =>
  apiFetch(`/alertas/${id}/leida`, { method: 'PATCH', body: { leida } })

export const marcarTodasLeidas = () => apiFetch('/alertas/marcar-todas-leidas', { method: 'POST' })
