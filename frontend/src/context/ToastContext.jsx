import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import Toast from '../components/Toast.jsx'
import { alNotificar } from '../utils/notificar.js'

// Duración en milisegundos: los errores permanecen más tiempo en pantalla.
const DURACIONES = { error: 7000, exito: 4500, info: 4500 }
// Máximo de toasts visibles a la vez (los más antiguos se descartan).
const MAXIMO = 4

const ToastContext = createContext(null)

/**
 * Capa global de toasts (mejora #9 del plan al siguiente nivel).
 *
 * - Se suscribe al bus `notificar()` para que el cliente HTTP pueda emitir
 *   avisos globales (sesión expirada, fallo de conexión, errores de servidor).
 * - Red de seguridad para promesas rechazadas sin capturar: hoy esos errores
 *   desaparecían en silencio.
 * - Deduplicación: varias peticiones paralelas con el mismo fallo producen un
 *   solo toast (se refresca su temporizador en lugar de apilar duplicados).
 */
export function ToastProvider({ children }) {
  const [avisos, setAvisos] = useState([])
  const temporizadores = useRef(new Map())

  const cerrar = useCallback((clave) => {
    setAvisos((lista) => lista.filter((aviso) => aviso.clave !== clave))
    const temporizador = temporizadores.current.get(clave)
    if (temporizador) {
      clearTimeout(temporizador)
      temporizadores.current.delete(clave)
    }
  }, [])

  const programarCierre = useCallback(
    (clave, tipo) => {
      const previo = temporizadores.current.get(clave)
      if (previo) clearTimeout(previo)
      const duracion = DURACIONES[tipo] ?? DURACIONES.info
      temporizadores.current.set(
        clave,
        setTimeout(() => {
          temporizadores.current.delete(clave)
          setAvisos((lista) => lista.filter((aviso) => aviso.clave !== clave))
        }, duracion),
      )
    },
    [],
  )

  const mostrar = useCallback(
    (tipo = 'info', mensaje, opciones = {}) => {
      if (!mensaje) return
      const aviso = { tipo, mensaje, clave: opciones.clave || `${tipo}|${mensaje}` }
      setAvisos((lista) => {
        const existe = lista.some((item) => item.clave === aviso.clave)
        if (existe) return lista.map((item) => (item.clave === aviso.clave ? aviso : item))
        const recortada = lista.length >= MAXIMO ? lista.slice(-(MAXIMO - 1)) : lista
        return [...recortada, aviso]
      })
      programarCierre(aviso.clave, tipo)
    },
    [programarCierre],
  )

  // Bus de notificaciones (emissions del cliente HTTP y de cualquier módulo).
  useEffect(
    () => alNotificar(({ tipo, mensaje, origen }) => mostrar(tipo, mensaje, { clave: origen ? `${origen}|${mensaje}` : undefined })),
    [mostrar],
  )

  // Red de seguridad: promesas rechazadas sin capturar (errores inesperados).
  useEffect(() => {
    function alRechazo(evento) {
      const razon = evento?.reason
      const mensaje =
        typeof razon === 'string'
          ? razon
          : razon?.message || 'Se produjo un error inesperado en la aplicación.'
      mostrar('error', mensaje)
    }
    window.addEventListener('unhandledrejection', alRechazo)
    return () => window.removeEventListener('unhandledrejection', alRechazo)
  }, [mostrar])

  // Limpieza de temporizadores al desmontar.
  useEffect(
    () => () => {
      temporizadores.current.forEach((temporizador) => clearTimeout(temporizador))
      temporizadores.current.clear()
    },
    [],
  )

  const valor = useMemo(
    () => ({ mostrar, cerrar, error: (m) => mostrar('error', m), exito: (m) => mostrar('exito', m), info: (m) => mostrar('info', m) }),
    [mostrar, cerrar],
  )

  return (
    <ToastContext.Provider value={valor}>
      {children}
      <Toast avisos={avisos} onCerrar={cerrar} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const contexto = useContext(ToastContext)
  if (!contexto) throw new Error('useToast debe usarse dentro de ToastProvider')
  return contexto
}
