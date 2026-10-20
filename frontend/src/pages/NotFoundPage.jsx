import { Link, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext.jsx'

/**
 * Página 404 propia (mejora #9 del plan al siguiente nivel).
 *
 * Sustituye la redirección silenciosa a "/" para las rutas desconocidas: el
 * usuario ve qué ruta falló y dispone de salida según su sesión.
 */
export default function NotFoundPage() {
  const { pathname } = useLocation()
  const { usuario, cargando } = useAuth()

  if (cargando) return <div className="cargando-pantalla">Cargando…</div>

  return (
    <div className="no-encontrada-pantalla">
      <section className="no-encontrada-tarjeta">
        <span className="no-encontrada-logo" aria-hidden="true">
          ⚖️
        </span>
        <p className="no-encontrada-codigo">404</p>
        <h1>Página no encontrada</h1>
        <p className="no-encontrada-texto">
          La dirección <code className="no-encontrada-ruta">{pathname}</code> no corresponde a
          ninguna sección de LegalVault. Puede que el enlace esté obsoleto o que la ruta se
          haya escrito mal.
        </p>

        <div className="no-encontrada-acciones">
          {usuario ? (
            <>
              <Link className="boton boton-primario" to="/">
                Volver al panel
              </Link>
              <Link className="boton" to="/expedientes">
                Ver expedientes
              </Link>
            </>
          ) : (
            <Link className="boton boton-primario" to="/login">
              Iniciar sesión
            </Link>
          )}
        </div>

        <p className="nota">LegalVault · gestión jurídica segura</p>
      </section>
    </div>
  )
}
