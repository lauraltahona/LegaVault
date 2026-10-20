// Pruebas del cliente HTTP: mensajes amigables + avisos globales (toast).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch, clearToken, getToken, setToken, setUnauthorizedHandler } from '../src/api/client.js'
import { alNotificar } from '../src/utils/notificar.js'

/** Respuesta simulada de fetch con los métodos que usa apiFetch. */
function respuesta(status, cuerpo) {
  const texto = JSON.stringify(cuerpo)
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => JSON.parse(texto),
    text: async () => texto,
  }
}

describe('apiFetch (cliente HTTP)', () => {
  let recibidas = []
  let cancelar = null

  beforeEach(() => {
    recibidas = []
    cancelar = alNotificar((n) => recibidas.push(n))
    localStorage.clear()
  })

  afterEach(() => {
    if (cancelar) cancelar()
    vi.unstubAllGlobals()
    setUnauthorizedHandler(null)
    clearToken()
  })

  it('una respuesta correcta no emite avisos', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(200, { id: 1 })))

    const datos = await apiFetch('/expedientes')

    expect(datos).toEqual({ id: 1 })
    expect(recibidas).toEqual([])
  })

  describe('fallo de conexión (backend inaccesible)', () => {
    it('lanza ApiError con mensaje amigable en español (estado 0) y avisa globalmente', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

      const promesa = apiFetch('/documentos')
      await expect(promesa).rejects.toThrow(ApiError)
      await expect(apiFetch('/documentos').catch((e) => e)).resolves.toMatchObject({
        estado: 0,
        message: expect.stringContaining('No se pudo conectar con el servidor'),
      })

      expect(recibidas).toHaveLength(2)
      expect(recibidas[0]).toMatchObject({
        tipo: 'error',
        origen: 'conexion',
        mensaje: expect.stringContaining('No se pudo conectar con el servidor'),
      })
    })
  })

  describe('401 (sesión expirada o inválida)', () => {
    it('con token previo avisa globalmente, limpia el token y notifica al manejador', async () => {
      setToken('token-viejo')
      const manejador = vi.fn()
      setUnauthorizedHandler(manejador)
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(401, { detail: 'Token expirado' })))

      const error = await apiFetch('/expedientes').catch((e) => e)

      expect(error).toBeInstanceOf(ApiError)
      expect(error.estado).toBe(401)
      expect(getToken()).toBeNull()
      expect(manejador).toHaveBeenCalledTimes(1)
      expect(recibidas).toHaveLength(1)
      expect(recibidas[0]).toMatchObject({ origen: 'sesion', tipo: 'error' })
    })

    it('sin token previo no avisa de sesión expirada (no hay sesión que avisar)', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(401, { detail: 'No autenticado' })))

      await apiFetch('/expedientes').catch(() => {})

      expect(recibidas).toEqual([])
    })

    it('un fallo de credenciales en /auth/login no dispara el aviso de sesión', async () => {
      setToken('token-viejo')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(401, { detail: 'Credenciales inválidas' })))

      const error = await apiFetch('/auth/login', {
        method: 'POST',
        omitirManejador: true,
      }).catch((e) => e)

      expect(error.estado).toBe(401)
      expect(recibidas).toEqual([])
      // El manejador global queda intacto: el login maneja su error inline.
      expect(getToken()).toBe('token-viejo')
    })

    it('la restauración de sesión (/auth/me) sí avisa, aunque use omitirManejador', async () => {
      setToken('token-caducado')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(401, { detail: 'Token expirado' })))

      await apiFetch('/auth/me', { omitirManejador: true }).catch(() => {})

      expect(recibidas).toHaveLength(1)
      expect(recibidas[0]).toMatchObject({ origen: 'sesion' })
      // Comportamiento previo conservado: con omitirManejador no se limpia aquí.
      expect(getToken()).toBe('token-caducado')
    })
  })

  describe('errores 5xx y 4xx', () => {
    it('un 5xx lanza ApiError y emite el aviso de error de servidor', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(500, { detail: 'Fallo interno' })))

      const error = await apiFetch('/documentos').catch((e) => e)

      expect(error.estado).toBe(500)
      expect(error.message).toBe('Fallo interno')
      expect(recibidas).toHaveLength(1)
      expect(recibidas[0]).toMatchObject({
        origen: 'servidor',
        mensaje: expect.stringContaining('HTTP 500'),
      })
    })

    it('un 403/409 contextuales NO genera aviso global (el error queda inline en la pantalla)', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuesta(403, { detail: 'Permiso denegado' })))

      const error = await apiFetch('/expedientes/1').catch((e) => e)

      expect(error.estado).toBe(403)
      expect(recibidas).toEqual([])
    })
  })
})
