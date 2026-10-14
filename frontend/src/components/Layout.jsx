import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext.jsx'
import { ROLES } from '../constants.js'

const enlaces = [
  { to: '/', etiqueta: 'Panel', icono: '▤', exacto: true },
  { to: '/expedientes', etiqueta: 'Expedientes', icono: '🗂' },
  { to: '/documentos', etiqueta: 'Documentos', icono: '📄' },
  { to: '/usuarios', etiqueta: 'Usuarios', icono: '👤', soloAdmin: true },
  { to: '/alertas', etiqueta: 'Alertas', icono: '🔔', soloAdmin: true },
]

export default function Layout() {
  const { usuario, esAdmin, logout } = useAuth()
  const navigate = useNavigate()

  async function salir() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="marca">
          <span className="marca-logo">⚖️</span>
          <div>
            <strong>LegalVault</strong>
            <small>Gestión jurídica segura</small>
          </div>
        </div>

        <nav className="nav">
          {enlaces
            .filter((enlace) => !enlace.soloAdmin || esAdmin)
            .map((enlace) => (
              <NavLink
                key={enlace.to}
                to={enlace.to}
                end={enlace.exacto}
                className={({ isActive }) => `nav-item${isActive ? ' activo' : ''}`}
              >
                <span className="nav-icono">{enlace.icono}</span>
                {enlace.etiqueta}
              </NavLink>
            ))}
        </nav>

        <div className="sidebar-pie">
          <div className="usuario-info">
            <strong>{usuario?.nombre_completo}</strong>
            <small>
              {usuario?.username} · {ROLES[usuario?.rol] ?? usuario?.rol}
            </small>
          </div>
          <button type="button" className="boton boton-fantasma" onClick={salir}>
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="contenido">
        <Outlet />
      </main>
    </div>
  )
}
