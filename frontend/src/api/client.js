// Cliente HTTP centralizado.
//
// - Adjunta automáticamente el token JWT de la sesión.
// - Normaliza los errores del backend en un objeto `ApiError`.
// - Notifica a la aplicación cuando un token deja de ser válido (401).

const API_URL = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'legalvault_token'

let alNoAutorizado = null

export class ApiError extends Error {
  constructor(mensaje, estado) {
    super(mensaje)
    this.name = 'ApiError'
    this.estado = estado
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/** Registra el manejador que se ejecuta cuando la sesión expira. */
export function setUnauthorizedHandler(handler) {
  alNoAutorizado = handler
}

/** Serializa un objeto como query string, ignorando valores vacíos. */
export function query(parametros = {}) {
  const partes = Object.entries(parametros)
    .filter(([, valor]) => valor !== undefined && valor !== null && valor !== '' && valor !== false)
    .map(([clave, valor]) => `${encodeURIComponent(clave)}=${encodeURIComponent(valor)}`)
  return partes.length ? `?${partes.join('&')}` : ''
}

export async function apiFetch(path, opciones = {}) {
  const { method = 'GET', body, isForm = false, raw = false, omitirManejador = false } = opciones

  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let payload = body
  if (body instanceof FormData) {
    payload = body
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const respuesta = await fetch(`${API_URL}${path}`, { method, headers, body: payload })

  if (respuesta.status === 401 && !omitirManejador) {
    clearToken()
    if (alNoAutorizado) alNoAutorizado()
  }

  if (!respuesta.ok) {
    let detalle = `Error ${respuesta.status}`
    try {
      const datos = await respuesta.json()
      detalle = datos?.detail || detalle
    } catch {
      // El cuerpo no era JSON; se conserva el mensaje por defecto.
    }
    throw new ApiError(detalle, respuesta.status)
  }

  if (raw) return respuesta
  if (respuesta.status === 204) return null

  const texto = await respuesta.text()
  return texto ? JSON.parse(texto) : null
}

/** Descarga un archivo protegido y lanza la descarga en el navegador. */
export async function descargarArchivo(path, nombre) {
  const respuesta = await apiFetch(path, { raw: true })
  const blob = await respuesta.blob()
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
}
