import { Navigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext.jsx'

/** Envuelve rutas que requieren sesión y, opcionalmente, ciertos roles. */
export default function RutaProtegida({ roles, children }) {
  const { usuario, cargando } = useAuth()

  if (cargando) return <div className="cargando-pantalla">Cargando…</div>
  if (!usuario) return <Navigate to="/login" replace />
  if (roles && !roles.includes(usuario.rol)) return <Navigate to="/" replace />

  return children
}
