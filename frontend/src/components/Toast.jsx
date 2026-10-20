/** Notificación flotante (toast). Presentacional: recibe la lista y el cierre. */

const ICONOS = { error: '⚠️', exito: '✔', info: 'ℹ️' }
const TITULOS = { error: 'Error', exito: 'Listo', info: 'Aviso' }

export default function Toast({ avisos = [], onCerrar = () => {} }) {
  if (!avisos.length) return null

  return (
    <div className="toast-contenedor" role="region" aria-label="Notificaciones">
      {avisos.map((aviso) => (
        <div
          key={aviso.clave}
          className={`toast toast-${aviso.tipo}`}
          role={aviso.tipo === 'error' ? 'alert' : 'status'}
        >
          <span className="toast-icono" aria-hidden="true">
            {ICONOS[aviso.tipo] ?? ICONOS.info}
          </span>
          <div className="toast-cuerpo">
            <strong>{TITULOS[aviso.tipo] ?? TITULOS.info}</strong>
            <span>{aviso.mensaje}</span>
          </div>
          <button
            type="button"
            className="toast-cerrar"
            aria-label="Cerrar notificación"
            onClick={() => onCerrar(aviso.clave)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
