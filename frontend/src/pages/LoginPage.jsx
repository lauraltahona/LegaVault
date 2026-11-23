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
          <p>Custodia criptográfica y gestión de expedientes jurídicos</p>
        </div>

        <Aviso tipo="error">{error}</Aviso>

        <label className="campo">
          <span>Usuario</span>
          <input
            type="text"
            placeholder="Introduce tu usuario..."
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
            placeholder="Introduce tu contraseña..."
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        <button type="submit" className="boton boton-primario boton-bloque" disabled={enviando}>
          {enviando ? 'Verificando credenciales…' : 'Acceder al Sistema Seguramente →'}
        </button>

        <div className="login-ayuda">
          <span>Credencial demo rápida:</span> <code>admin / Admin123!</code>
        </div>
      </form>
    </div>
  )
}
