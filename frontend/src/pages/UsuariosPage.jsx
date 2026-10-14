import { useEffect, useState } from 'react'

import Aviso from '../components/Aviso.jsx'
import Insignia from '../components/Insignia.jsx'
import Modal from '../components/Modal.jsx'
import {
  actualizarUsuario,
  cambiarEstadoUsuario,
  crearUsuario,
  desbloquearUsuario,
  listarUsuarios,
  restablecerPassword,
} from '../api/usuarios.js'
import { ROLES, opciones } from '../constants.js'
import { fechaHora } from '../utils/format.js'

const VACIO = { username: '', nombre_completo: '', email: '', password: '', rol: 'abogado' }

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([])
  const [filtros, setFiltros] = useState({ q: '', rol: '', activo: '' })
  const [formulario, setFormulario] = useState(null)
  const [editandoId, setEditandoId] = useState(null)
  const [cambioPassword, setCambioPassword] = useState(null)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')
  const [cargando, setCargando] = useState(true)

  async function cargar() {
    setCargando(true)
    try {
      const datos = await listarUsuarios(filtros)
      setUsuarios(datos)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    const temporizador = setTimeout(cargar, 250)
    return () => clearTimeout(temporizador)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.q, filtros.rol, filtros.activo])

  function abrirCrear() {
    setError('')
    setExito('')
    setEditandoId(null)
    setFormulario({ ...VACIO })
  }

  function abrirEditar(usuario) {
    setError('')
    setExito('')
    setEditandoId(usuario.id)
    setFormulario({
      username: usuario.username,
      nombre_completo: usuario.nombre_completo,
      email: usuario.email,
      rol: usuario.rol,
    })
  }

  async function guardar(evento) {
    evento.preventDefault()
    setError('')
    try {
      if (editandoId) {
        await actualizarUsuario(editandoId, {
          nombre_completo: formulario.nombre_completo,
          email: formulario.email,
          rol: formulario.rol,
        })
      } else {
        await crearUsuario(formulario)
      }
      setFormulario(null)
      setExito(editandoId ? 'Usuario actualizado.' : 'Usuario creado.')
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  async function cambiarEstado(usuario) {
    const accion = usuario.activo ? 'desactivar' : 'activar'
    if (!window.confirm(`¿Desea ${accion} la cuenta de ${usuario.username}?`)) return
    setError('')
    try {
      await cambiarEstadoUsuario(usuario.id, !usuario.activo)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  async function desbloquear(usuario) {
    setError('')
    try {
      await desbloquearUsuario(usuario.id)
      setExito(`Cuenta de ${usuario.username} desbloqueada.`)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  async function guardarPassword(evento) {
    evento.preventDefault()
    setError('')
    try {
      await restablecerPassword(cambioPassword.usuario.id, cambioPassword.nueva)
      setCambioPassword(null)
      setExito('Contraseña restablecida.')
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Usuarios</h1>
          <p className="subtitulo">Cuentas, roles y estado de bloqueo.</p>
        </div>
        <button type="button" className="boton boton-primario" onClick={abrirCrear}>
          + Nuevo usuario
        </button>
      </header>

      <Aviso tipo="error">{error}</Aviso>
      <Aviso tipo="ok">{exito}</Aviso>

      <section className="panel">
        <div className="filtros">
          <input
            type="search"
            placeholder="Buscar por usuario, nombre o correo…"
            value={filtros.q}
            onChange={(e) => setFiltros({ ...filtros, q: e.target.value })}
          />
          <select value={filtros.rol} onChange={(e) => setFiltros({ ...filtros, rol: e.target.value })}>
            <option value="">Todos los roles</option>
            {opciones(ROLES).map(({ valor, etiqueta }) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
          <select
            value={filtros.activo}
            onChange={(e) => setFiltros({ ...filtros, activo: e.target.value })}
          >
            <option value="">Todos los estados</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
        </div>

        {cargando ? (
          <p className="vacio">Cargando…</p>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Último acceso</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => (
                <tr key={usuario.id}>
                  <td>{usuario.username}</td>
                  <td>{usuario.nombre_completo}</td>
                  <td>{usuario.email}</td>
                  <td>{ROLES[usuario.rol] ?? usuario.rol}</td>
                  <td>
                    <div className="celda-badges">
                      <Insignia tono={usuario.activo ? 'verde' : 'gris'}>
                        {usuario.activo ? 'Activo' : 'Inactivo'}
                      </Insignia>
                      {usuario.esta_bloqueado && <Insignia tono="rojo">Bloqueado</Insignia>}
                    </div>
                  </td>
                  <td>{fechaHora(usuario.ultimo_acceso)}</td>
                  <td className="acciones">
                    <button type="button" className="boton boton-mini" onClick={() => abrirEditar(usuario)}>
                      Editar
                    </button>
                    <button
                      type="button"
                      className="boton boton-mini"
                      onClick={() => setCambioPassword({ usuario, nueva: '' })}
                    >
                      Contraseña
                    </button>
                    {usuario.esta_bloqueado && (
                      <button type="button" className="boton boton-mini" onClick={() => desbloquear(usuario)}>
                        Desbloquear
                      </button>
                    )}
                    <button
                      type="button"
                      className={`boton boton-mini ${usuario.activo ? 'boton-peligro' : 'boton-ok'}`}
                      onClick={() => cambiarEstado(usuario)}
                    >
                      {usuario.activo ? 'Desactivar' : 'Activar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {formulario && (
        <Modal
          titulo={editandoId ? 'Editar usuario' : 'Nuevo usuario'}
          onCerrar={() => setFormulario(null)}
        >
          <form className="formulario" onSubmit={guardar}>
            <Aviso tipo="error">{error}</Aviso>

            <label className="campo">
              <span>Nombre de usuario *</span>
              <input
                value={formulario.username}
                onChange={(e) => setFormulario({ ...formulario, username: e.target.value })}
                disabled={Boolean(editandoId)}
                required
              />
            </label>

            <label className="campo">
              <span>Nombre completo *</span>
              <input
                value={formulario.nombre_completo}
                onChange={(e) => setFormulario({ ...formulario, nombre_completo: e.target.value })}
                required
              />
            </label>

            <label className="campo">
              <span>Correo electrónico *</span>
              <input
                type="email"
                value={formulario.email}
                onChange={(e) => setFormulario({ ...formulario, email: e.target.value })}
                required
              />
            </label>

            <label className="campo">
              <span>Rol *</span>
              <select
                value={formulario.rol}
                onChange={(e) => setFormulario({ ...formulario, rol: e.target.value })}
              >
                {opciones(ROLES).map(({ valor, etiqueta }) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </label>

            {!editandoId && (
              <label className="campo">
                <span>Contraseña *</span>
                <input
                  type="password"
                  value={formulario.password}
                  onChange={(e) => setFormulario({ ...formulario, password: e.target.value })}
                  placeholder="Mínimo 8 caracteres, con letras y números"
                  required
                />
              </label>
            )}

            <div className="formulario-acciones">
              <button type="button" className="boton" onClick={() => setFormulario(null)}>
                Cancelar
              </button>
              <button type="submit" className="boton boton-primario">
                {editandoId ? 'Guardar cambios' : 'Crear usuario'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {cambioPassword && (
        <Modal
          titulo={`Restablecer contraseña de ${cambioPassword.usuario.username}`}
          onCerrar={() => setCambioPassword(null)}
        >
          <form className="formulario" onSubmit={guardarPassword}>
            <Aviso tipo="error">{error}</Aviso>
            <label className="campo">
              <span>Nueva contraseña *</span>
              <input
                type="password"
                value={cambioPassword.nueva}
                onChange={(e) => setCambioPassword({ ...cambioPassword, nueva: e.target.value })}
                placeholder="Mínimo 8 caracteres, con letras y números"
                autoFocus
                required
              />
            </label>
            <div className="formulario-acciones">
              <button type="button" className="boton" onClick={() => setCambioPassword(null)}>
                Cancelar
              </button>
              <button type="submit" className="boton boton-primario">
                Guardar
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
