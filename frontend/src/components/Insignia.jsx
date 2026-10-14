/** Etiqueta de color según un valor y su mapa de estilos. */
export default function Insignia({ children, tono = 'neutro' }) {
  return <span className={`insignia insignia-${tono}`}>{children}</span>
}

export function tonoEstado(estado) {
  switch (estado) {
    case 'abierto':
      return 'verde'
    case 'en_tramite':
      return 'azul'
    case 'suspendido':
      return 'ambar'
    case 'cerrado':
      return 'gris'
    case 'archivado':
      return 'gris'
    default:
      return 'neutro'
  }
}

export function tonoSeveridad(severidad) {
  switch (severidad) {
    case 'critica':
      return 'rojo'
    case 'advertencia':
      return 'ambar'
    case 'info':
      return 'azul'
    default:
      return 'neutro'
  }
}

export function tonoSensibilidad(nivel) {
  switch (nivel) {
    case 'confidencial':
      return 'rojo'
    case 'interno':
      return 'ambar'
    case 'publico':
      return 'verde'
    default:
      return 'neutro'
  }
}
