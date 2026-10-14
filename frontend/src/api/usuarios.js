import { apiFetch, query } from './client.js'

export const listarUsuarios = (filtros = {}) => apiFetch(`/usuarios${query(filtros)}`)

export const listarSeleccionUsuarios = () => apiFetch('/usuarios/seleccion')

export const crearUsuario = (datos) => apiFetch('/usuarios', { method: 'POST', body: datos })

export const actualizarUsuario = (id, datos) => apiFetch(`/usuarios/${id}`, { method: 'PUT', body: datos })

export const cambiarEstadoUsuario = (id, activo) =>
  apiFetch(`/usuarios/${id}/estado`, { method: 'PATCH', body: { activo } })

export const restablecerPassword = (id, nuevaPassword) =>
  apiFetch(`/usuarios/${id}/password`, { method: 'POST', body: { nueva_password: nuevaPassword } })

export const desbloquearUsuario = (id) => apiFetch(`/usuarios/${id}/desbloquear`, { method: 'POST' })
