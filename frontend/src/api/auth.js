import { apiFetch } from './client.js'

export const iniciarSesion = (username, password) =>
  apiFetch('/auth/login', { method: 'POST', body: { username, password }, omitirManejador: true })

export const cerrarSesion = () => apiFetch('/auth/logout', { method: 'POST' })

export const usuarioActual = () => apiFetch('/auth/me', { omitirManejador: true })
