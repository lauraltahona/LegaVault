// Bus de notificaciones (toast) sin dependencias.
//
// Permite que módulos "puros" (como el cliente HTTP) avisen a la capa React
// sin importar contexto alguno: quien emite llama a `notificar()` y el
// `ToastProvider` se suscribe con `alNotificar()`.
//
// Formato de una notificación:
//   { tipo: 'error' | 'exito' | 'info', mensaje: string, origen?: string }

const suscriptores = new Set()

function emitirA(suscriptor, notificacion) {
  try {
    suscriptor(notificacion)
  } catch {
    // Un suscriptor defectuoso no interrumpe a los demás.
  }
}

/** Emite una notificación a todos los suscriptores activos. */
export function notificar(notificacion) {
  const mensaje = typeof notificacion === 'string' ? notificacion : notificacion?.mensaje
  if (!mensaje) return
  const normalizada = {
    tipo: notificacion?.tipo || 'info',
    mensaje,
    origen: notificacion?.origen,
  }
  suscriptores.forEach((suscriptor) => emitirA(suscriptor, normalizada))
}

/**
 * Se suscribe al bus. Devuelve la función para cancelar la suscripción.
 * Notificaciones emitidas sin suscriptores se descartan (en la aplicación el
 * `ToastProvider` monta antes de cualquier llamada a la API).
 */
export function alNotificar(suscriptor) {
  suscriptores.add(suscriptor)
  return () => suscriptores.delete(suscriptor)
}
