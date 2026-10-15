import { useState } from 'react'

import Aviso from './Aviso.jsx'
import Modal from './Modal.jsx'
import { agregarEntrada, cambiarCredenciales, desbloquearBoveda } from '../api/bovedas.js'

/**
 * Desbloqueo de una bóveda (Módulo 4).
 *
 * Primero pide la contraseña; según cuál se introduzca se mostrará uno u otro
 * contenido. Una vez abierta, permite añadir entradas a esa vista o cambiar su
 * contraseña sin afectar a la otra.
 */
export default function AbrirBovedaModal({ boveda, onCerrar, onCambio }) {
  const [password, setPassword] = useState('')
  const [entradas, setEntradas] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [trabajando, setTrabajando] = useState(false)
  const [nueva, setNueva] = useState({ titulo: '', contenido: '' })
  const [credenciales, setCredenciales] = useState({ actual: '', nueva: '' })
  const [mostrarCambio, setMostrarCambio] = useState(false)

  async function desbloquear(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    setTrabajando(true)
    try {
      const contenido = await desbloquearBoveda(boveda.id, password)
      setEntradas(contenido.entradas ?? [])
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  async function recargar() {
    const contenido = await desbloquearBoveda(boveda.id, password)
    setEntradas(contenido.entradas ?? [])
  }

  async function agregar(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    setTrabajando(true)
    try {
      await agregarEntrada(boveda.id, { ...nueva, password })
      setNueva({ titulo: '', contenido: '' })
      await recargar()
      setAviso('Entrada añadida a esta vista.')
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  async function cambiar(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    if (credenciales.nueva.length < 8) {
      setError('La nueva contraseña debe tener al menos 8 caracteres.')
      return
    }
    setTrabajando(true)
    try {
      await cambiarCredenciales(boveda.id, {
        password_actual: credenciales.actual || password,
        password_nueva: credenciales.nueva,
      })
      setPassword(credenciales.nueva)
      setCredenciales({ actual: '', nueva: '' })
      setMostrarCambio(false)
      setAviso('Contraseña actualizada. Use la nueva para volver a abrir esta vista.')
      onCambio?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  const abierta = entradas !== null

  return (
    <Modal titulo={`Bóveda: ${boveda.nombre}`} onCerrar={onCerrar} ancho="640px">
      <Aviso tipo="error">{error}</Aviso>
      <Aviso tipo="ok">{aviso}</Aviso>

      {!abierta ? (
        <form className="formulario" onSubmit={desbloquear}>
          <p className="nota">
            Introduzca una de las contraseñas de la bóveda. Cada contraseña muestra su propio
            contenido.
          </p>
          <label className="campo">
            <span>Contraseña</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              required
            />
          </label>
          <div className="formulario-acciones">
            <button type="button" className="boton" onClick={onCerrar}>
              Cancelar
            </button>
            <button type="submit" className="boton boton-primario" disabled={trabajando}>
              {trabajando ? 'Comprobando…' : 'Desbloquear'}
            </button>
          </div>
        </form>
      ) : (
        <div className="formulario">
          <div className="boveda-contenido">
            {entradas.length === 0 ? (
              <p className="vacio">Esta vista aún no tiene entradas.</p>
            ) : (
              <ul className="lista-entradas">
                {entradas.map((entrada) => (
                  <li key={entrada.id} className="entrada">
                    <strong>{entrada.titulo}</strong>
                    <p>{entrada.contenido}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form className="formulario" onSubmit={agregar}>
            <h3>Añadir entrada a esta vista</h3>
            <div className="rejilla-form">
              <label className="campo">
                <span>Título</span>
                <input
                  value={nueva.titulo}
                  onChange={(e) => setNueva({ ...nueva, titulo: e.target.value })}
                  required
                />
              </label>
              <label className="campo">
                <span>Contenido</span>
                <input
                  value={nueva.contenido}
                  onChange={(e) => setNueva({ ...nueva, contenido: e.target.value })}
                  required
                />
              </label>
            </div>
            <div className="formulario-acciones">
              <button type="submit" className="boton boton-ok" disabled={trabajando}>
                Añadir entrada
              </button>
            </div>
          </form>

          {mostrarCambio ? (
            <form className="formulario" onSubmit={cambiar}>
              <h3>Cambiar la contraseña de esta vista</h3>
              <div className="rejilla-form">
                <label className="campo">
                  <span>Contraseña actual</span>
                  <input
                    type="password"
                    value={credenciales.actual}
                    onChange={(e) =>
                      setCredenciales({ ...credenciales, actual: e.target.value })
                    }
                    placeholder="(la de esta sesión)"
                    required
                  />
                </label>
                <label className="campo">
                  <span>Nueva contraseña</span>
                  <input
                    type="password"
                    value={credenciales.nueva}
                    onChange={(e) => setCredenciales({ ...credenciales, nueva: e.target.value })}
                    minLength={8}
                    required
                  />
                </label>
              </div>
              <div className="formulario-acciones">
                <button
                  type="button"
                  className="boton"
                  onClick={() => setMostrarCambio(false)}
                >
                  Cancelar
                </button>
                <button type="submit" className="boton boton-primario" disabled={trabajando}>
                  Guardar
                </button>
              </div>
            </form>
          ) : (
            <div className="formulario-acciones">
              <button
                type="button"
                className="boton boton-mini"
                onClick={() => setMostrarCambio(true)}
              >
                Cambiar contraseña de esta vista
              </button>
              <button type="button" className="boton boton-mini" onClick={onCerrar}>
                Cerrar
              </button>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
