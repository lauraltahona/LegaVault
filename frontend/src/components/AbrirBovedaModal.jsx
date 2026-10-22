import { useState } from 'react'

import Aviso from './Aviso.jsx'
import Modal from './Modal.jsx'
import {
  agregarEntrada,
  adjuntarArchivo,
  cambiarCredenciales,
  descargarAdjunto,
  desbloquearBoveda,
  eliminarAdjunto,
  modernizarBoveda,
  verificarAdjunto,
} from '../api/bovedas.js'
import { ARCHIVO_ACCEPT } from '../constants.js'

/** Formatea un tamaño en bytes de forma legible para la persona usuaria. */
function formatearTamano(bytes) {
  const valor = Number(bytes) || 0
  if (valor < 1024) return `${valor} B`
  if (valor < 1024 * 1024) return `${(valor / 1024).toFixed(1)} KB`
  return `${(valor / (1024 * 1024)).toFixed(2)} MB`
}

/**
 * Desbloqueo de una bóveda (Módulo 4).
 *
 * Primero pide la contraseña; según cuál se introduzca se mostrará uno u otro
 * contenido. Una vez abierta, permite añadir entradas a esa vista, cambiar su
 * contraseña sin afectar a la otra y, desde la **Fase 6**, **adjuntar y
 * descargar archivos** en ese mismo fondo.
 *
 * Las bóvedas heredadas (formato anterior, solo texto) siguen abriéndose
 * igual, pero no admiten adjuntos: la interfaz ofrece **modernizarlas**,
 * lo que exige las dos contraseñas (sin ellas el servidor no puede garantizar
 * que los dos fondos queden cifrados con el mismo tamaño).
 */
export default function AbrirBovedaModal({ boveda, onCerrar, onCambio }) {
  const [password, setPassword] = useState('')
  const [entradas, setEntradas] = useState(null)
  const [adjuntos, setAdjuntos] = useState([])
  const [version, setVersion] = useState(boveda.formato ?? 1)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [trabajando, setTrabajando] = useState(false)
  const [nueva, setNueva] = useState({ titulo: '', contenido: '' })
  const [credenciales, setCredenciales] = useState({ actual: '', nueva: '' })
  const [mostrarCambio, setMostrarCambio] = useState(false)
  // Adjuntos (Fase 6)
  const [archivoAdjunto, setArchivoAdjunto] = useState(null)
  const [tituloAdjunto, setTituloAdjunto] = useState('')
  const [verificaciones, setVerificaciones] = useState({})
  // Modernización de las bóvedas heredadas
  const [mostrarModernizar, setMostrarModernizar] = useState(false)
  const [modernizar, setModernizar] = useState({ visible: '', confidencial: '' })

  const esV1 = version < 2

  async function desbloquear(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    setTrabajando(true)
    try {
      const contenido = await desbloquearBoveda(boveda.id, password)
      setEntradas(contenido.entradas ?? [])
      setAdjuntos(contenido.adjuntos ?? [])
      setVersion(contenido.version ?? 2)
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  async function recargar() {
    const contenido = await desbloquearBoveda(boveda.id, password)
    setEntradas(contenido.entradas ?? [])
    setAdjuntos(contenido.adjuntos ?? [])
    setVersion(contenido.version ?? 2)
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

  // --- adjuntos (Fase 6) ------------------------------------------------
  async function adjuntar(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    if (!archivoAdjunto) {
      setError('Seleccione primero un archivo.')
      return
    }
    setTrabajando(true)
    try {
      await adjuntarArchivo(boveda.id, {
        password,
        archivo: archivoAdjunto,
        titulo: tituloAdjunto,
      })
      setArchivoAdjunto(null)
      setTituloAdjunto('')
      await recargar()
      setAviso(`Adjunto «${archivoAdjunto.name}» cargado en este fondo.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  async function descargar(adjunto) {
    setError('')
    setAviso('')
    setTrabajando(true)
    try {
      await descargarAdjunto(boveda.id, adjunto.id, password, adjunto.nombre)
      setAviso(`Adjunto «${adjunto.nombre}» descargado.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  async function verificar(adjunto) {
    setError('')
    setAviso('')
    setVerificaciones((previas) => ({
      ...previas,
      [adjunto.id]: { estado: 'comprobando', mensaje: 'Comprobando…' },
    }))
    try {
      const resultado = await verificarAdjunto(boveda.id, adjunto.id, password)
      setVerificaciones((previas) => ({
        ...previas,
        [adjunto.id]: {
          estado: resultado.integro ? 'integro' : 'roto',
          mensaje: resultado.mensaje,
        },
      }))
    } catch (err) {
      setVerificaciones((previas) => ({
        ...previas,
        [adjunto.id]: { estado: 'error', mensaje: err.message },
      }))
    }
  }

  async function eliminar(adjunto) {
    setError('')
    setAviso('')
    setTrabajando(true)
    try {
      await eliminarAdjunto(boveda.id, adjunto.id, password)
      await recargar()
      setAviso(`Adjunto «${adjunto.nombre}» eliminado de este fondo.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setTrabajando(false)
    }
  }

  // --- modernización de las bóvedas heredadas ---------------------------
  async function enviarModernizacion(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    if (modernizar.visible.length < 8 || modernizar.confidencial.length < 8) {
      setError('Las dos contraseñas deben tener al menos 8 caracteres.')
      return
    }
    if (modernizar.visible === modernizar.confidencial) {
      setError('Las dos contraseñas deben ser diferentes.')
      return
    }
    setTrabajando(true)
    try {
      await modernizarBoveda(boveda.id, {
        password_visible: modernizar.visible,
        password_confidencial: modernizar.confidencial,
      })
      setModernizar({ visible: '', confidencial: '' })
      setMostrarModernizar(false)
      setVersion(2)
      setAviso('Bóveda modernizada: ya admite archivos adjuntos.')
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

      {esV1 && !mostrarModernizar && (
        <Aviso tipo="error">
          Esta bóveda usa el formato anterior (solo texto). Modernícela para poder adjuntar
          archivos. <button type="button" className="boton boton-mini" onClick={() => setMostrarModernizar(true)}>
            Modernizar
          </button>
        </Aviso>
      )}

      {mostrarModernizar ? (
        <form className="formulario" onSubmit={enviarModernizacion}>
          <h3>Modernizar la bóveda</h3>
          <p className="nota">
            Se necesitan <strong>las dos contraseñas</strong>: el servidor debe poder abrir
            ambos fondos para cifrarlos con el mismo tamaño y garantizar que la bóveda ocupe
            siempre los mismos bytes en disco.
          </p>
          <div className="rejilla-form">
            <label className="campo">
              <span>Contraseña del Fondo 1 *</span>
              <input
                type="password"
                value={modernizar.visible}
                onChange={(e) => setModernizar({ ...modernizar, visible: e.target.value })}
                minLength={8}
                required
              />
            </label>
            <label className="campo">
              <span>Contraseña del Fondo 2 *</span>
              <input
                type="password"
                value={modernizar.confidencial}
                onChange={(e) => setModernizar({ ...modernizar, confidencial: e.target.value })}
                minLength={8}
                required
              />
            </label>
          </div>
          <div className="formulario-acciones">
            <button type="button" className="boton" onClick={() => setMostrarModernizar(false)}>
              Cancelar
            </button>
            <button type="submit" className="boton boton-primario" disabled={trabajando}>
              {trabajando ? 'Modernizando…' : 'Modernizar bóveda'}
            </button>
          </div>
        </form>
      ) : !abierta ? (
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

          {/* --- adjuntos del fondo abierto (Fase 6) --- */}
          <section className="formulario">
            <h3>Archivos adjuntos de este fondo</h3>
            {adjuntos.length === 0 ? (
              <p className="vacio">Este fondo todavía no tiene archivos adjuntos.</p>
            ) : (
              <ul className="lista-entradas">
                {adjuntos.map((adjunto) => {
                  const verificacion = verificaciones[adjunto.id]
                  return (
                    <li key={adjunto.id} className="entrada">
                      <strong>{adjunto.nombre}</strong>
                      <p>
                        {adjunto.mime} · {formatearTamano(adjunto.tamano_bytes)}
                      </p>
                      <small className="celda-hash">
                        SHA-256: {String(adjunto.sha256 ?? '').slice(0, 16)}…
                      </small>
                      {verificacion && (
                        <div className={`verificacion verificacion-${verificacion.estado}`}>
                          {verificacion.estado === 'integro' && '✅ '}
                          {verificacion.estado === 'roto' && '❌ '}
                          {verificacion.estado === 'error' && '⚠️ '}
                          {verificacion.mensaje}
                        </div>
                      )}
                      <div className="formulario-acciones">
                        <button
                          type="button"
                          className="boton boton-mini"
                          onClick={() => descargar(adjunto)}
                          disabled={trabajando}
                        >
                          Descargar
                        </button>
                        <button
                          type="button"
                          className="boton boton-mini"
                          onClick={() => verificar(adjunto)}
                          disabled={trabajando}
                        >
                          Verificar integridad
                        </button>
                        <button
                          type="button"
                          className="boton boton-mini boton-peligro"
                          onClick={() => eliminar(adjunto)}
                          disabled={trabajando}
                        >
                          Eliminar
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}

            <form className="formulario" onSubmit={adjuntar}>
              <label className="campo">
                <span>Adjuntar un archivo a este fondo</span>
                <input
                  type="file"
                  accept={ARCHIVO_ACCEPT}
                  disabled={esV1}
                  onChange={(e) => setArchivoAdjunto(e.target.files?.[0] ?? null)}
                />
              </label>
              <label className="campo">
                <span>Etiqueta (opcional)</span>
                <input
                  value={tituloAdjunto}
                  maxLength={200}
                  onChange={(e) => setTituloAdjunto(e.target.value)}
                  placeholder="Por ejemplo: contrato de arrendamiento"
                />
              </label>
              {esV1 ? (
                <p className="nota">
                  Las bóvedas en formato anterior no admiten adjuntos: modernice la bóveda para
                  poder subirlos.
                </p>
              ) : (
                <div className="formulario-acciones">
                  <button type="submit" className="boton boton-ok" disabled={trabajando}>
                    Adjuntar
                  </button>
                </div>
              )}
            </form>
          </section>

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
