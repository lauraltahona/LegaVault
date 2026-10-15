import { apiFetch, query } from './client.js'

export const listarAuditoria = (filtros = {}) => apiFetch(`/auditoria${query(filtros)}`)

export const verificarAuditoria = () => apiFetch('/auditoria/verificar')

export const resumenAuditoria = () => apiFetch('/auditoria/resumen')
