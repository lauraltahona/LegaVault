/** Ventana modal sencilla y reutilizable. */
export default function Modal({ titulo, children, onCerrar, ancho = '560px' }) {
  return (
    <div className="modal-fondo" onMouseDown={onCerrar}>
      <div
        className="modal"
        style={{ maxWidth: ancho }}
        onMouseDown={(evento) => evento.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <header className="modal-cabecera">
          <h2>{titulo}</h2>
          <button type="button" className="boton-icono" onClick={onCerrar} aria-label="Cerrar">
            ✕
          </button>
        </header>
        <div className="modal-cuerpo">{children}</div>
      </div>
    </div>
  )
}
