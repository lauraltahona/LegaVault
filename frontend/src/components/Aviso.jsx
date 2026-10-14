/** Mensaje de error o confirmación. */
export default function Aviso({ tipo = 'error', children }) {
  if (!children) return null
  return <div className={`aviso aviso-${tipo}`}>{children}</div>
}
