import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import Aviso from '../components/Aviso.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginPage() {
  const { usuario, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (usuario) return <Navigate to="/" replace />

  async function enviar(evento) {
    evento.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await login(username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message || 'No se pudo iniciar sesión.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="login-pantalla">
      <form className="login-tarjeta" onSubmit={enviar}>
        <div className="login-marca">
          <span className="marca-logo">⚖️</span>
          <h1>LegalVault</h1>
          <p>Sistema seguro de gestión de expedientes jurídicos</p>
        </div>

        <Aviso tipo="error">{error}</Aviso>

        <label className="campo">
          <span>Usuario</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>

        <label className="campo">
          <span>Contraseña</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        <button type="submit" className="boton boton-primario boton-bloque" disabled={enviando}>
          {enviando ? 'Accediendo…' : 'Iniciar sesión'}
        </button>

        <p className="login-ayuda">
          Demo: <code>admin / Admin123!</code>
        </p>
      </form>
    </div>
  )
}
