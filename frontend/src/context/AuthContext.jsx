import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { cerrarSesion, iniciarSesion, usuarioActual } from '../api/auth.js'
import { clearToken, getToken, setToken, setUnauthorizedHandler } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(true)

  // Si el backend responde 401, la sesión ya no es válida: se limpia.
  useEffect(() => {
    setUnauthorizedHandler(() => setUsuario(null))
  }, [])

  useEffect(() => {
    let activo = true
    async function restaurar() {
      if (!getToken()) {
        setCargando(false)
        return
      }
      try {
        const datos = await usuarioActual()
        if (activo) setUsuario(datos)
      } catch {
        clearToken()
      } finally {
        if (activo) setCargando(false)
      }
    }
    restaurar()
    return () => {
      activo = false
    }
  }, [])

  const login = useCallback(async (username, password) => {
    const datos = await iniciarSesion(username, password)
    setToken(datos.access_token)
    setUsuario(datos.usuario)
    return datos.usuario
  }, [])

  const logout = useCallback(async () => {
    try {
      await cerrarSesion()
    } catch {
      // Aunque falle la revocación en el servidor, se cierra la sesión local.
    }
    clearToken()
    setUsuario(null)
  }, [])

  const valor = useMemo(
    () => ({
      usuario,
      cargando,
      login,
      logout,
      esAdmin: usuario?.rol === 'admin',
      puedeGestionar: usuario?.rol === 'admin' || usuario?.rol === 'abogado',
      // Todos los roles autenticados pueden cargar documentos en expedientes
      // a los que tienen acceso (el asistente no puede marcarlos confidenciales).
      puedeCargar: ['admin', 'abogado', 'asistente'].includes(usuario?.rol),
    }),
    [usuario, cargando, login, logout],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return contexto
}
