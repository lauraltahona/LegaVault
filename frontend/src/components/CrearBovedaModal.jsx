import { useState } from 'react'

import Aviso from './Aviso.jsx'
import Modal from './Modal.jsx'
import { crearBoveda, adjuntarArchivo } from '../api/bovedas.js'
import { ARCHIVO_ACCEPT, CAPACIDADES_ADJUNTOS_MB } from '../constants.js'

/**
 * Formulario para crear una bóveda de doble fondo (Módulo 4).
 *
 * Se solicitan **dos contraseñas distintas**: cada una abrirá un contenido
 * independiente. La interfaz no revela en ningún momento cuál es cuál: las
 * etiquetas son neutras ("Fondo 1" / "Fondo 2").
 *
 * Desde la **Fase 6** la bóveda admite además **archivos adjuntos por fondo**
 * y una **capacidad** (1 / 5 / 25 MB). Los archivos se suben **después** de
 * crear la bóveda, con la contraseña del fondo correspondiente: si la subida
 * falla, la bóveda queda creada igualmente y se avisa de ello.
 */
export default function CrearBovedaModal({ expedientes, onCerrar, onCreada }) {
  const [campos, setCampos] = useState({
    nombre: '',
    descripcion: '',
    expediente_id: '',
    password_visible: '',
    password_confidencial: '',
    contenido_visible: '',
    contenido_confidencial: '',
    adjuntos_mb: 5,
  })
  const [archivos, setArchivos] = useState({ visible: null, confidencial: null })
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [enviando, setEnviando] = useState(false)

  function actualizar(clave, valor) {
    setCampos((previos) => ({ ...previos, [clave]: valor }))
  }

  function seleccionarArchivo(clave, evento) {
    const archivo = evento.target.files?.[0] ?? null
    setArchivos((previos) => ({ ...previos, [clave]: archivo }))
  }

  async function subirArchivo(bovedaId, password, archivo, titulo) {
    if (!archivo) return null
    return adjuntarArchivo(bovedaId, { password, archivo, titulo })
  }

  async function enviar(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')

    if (campos.password_visible.length < 8 || campos.password_confidencial.length < 8) {
      setError('Cada contraseña debe tener al menos 8 caracteres.')
      return
    }
    if (campos.password_visible === campos.password_confidencial) {
      setError('Las dos contraseñas deben ser diferentes.')
      return
    }

    setEnviando(true)
    try {
      const boveda = await crearBoveda(campos)

      // Los adjuntos se suben después: la bóveda ya existe y su tamaño en
      // disco es fijo, así que el orden no altera la negación plausible.
      const fallos = []
      for (const [clave, password, titulo] of [
        ['visible', campos.password_visible, 'Fondo 1'],
        ['confidencial', campos.password_confidencial, 'Fondo 2'],
      ]) {
        const archivo = archivos[clave]
        if (!archivo) continue
        try {
          await subirArchivo(boveda.id, password, archivo, titulo)
        } catch (err) {
          fallos.push(`${archivo.name}: ${err.message}`)
        }
      }

      onCreada?.()
      if (fallos.length) {
        // La bóveda **sí** se ha creado: solo los adjuntos han fallado.
        setAviso(
          `La bóveda se creó, pero no se pudieron subir estos archivos: ${fallos.join('; ')}. ` +
            'Puede adjuntarlos más tarde desde la bóveda.'
        )
        setEnviando(false)
        return
      }
      onCerrar()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal titulo="Nueva bóveda de doble fondo" onCerrar={onCerrar} ancho="640px">
      <form className="formulario" onSubmit={enviar}>
        <Aviso tipo="error">{error}</Aviso>
        <Aviso tipo="ok">{aviso}</Aviso>

        <p className="nota">
          Defina <strong>dos contraseñas diferentes</strong>. Cada una abre un contenido
          independiente dentro de la misma bóveda; no es posible saber cuál corresponde a cada
          una observando los datos almacenados.
        </p>

        <label className="campo">
          <span>Nombre *</span>
          <input
            value={campos.nombre}
            onChange={(e) => actualizar('nombre', e.target.value)}
            maxLength={120}
            required
          />
        </label>

        <label className="campo">
          <span>Descripción</span>
          <textarea
            rows={2}
            value={campos.descripcion}
            onChange={(e) => actualizar('descripcion', e.target.value)}
          />
        </label>

        <label className="campo">
          <span>Expediente asociado (opcional)</span>
          <select
            value={campos.expediente_id}
            onChange={(e) => actualizar('expediente_id', e.target.value)}
          >
            <option value="">Sin expediente</option>
            {expedientes.map((exp) => (
              <option key={exp.id} value={exp.id}>
                {exp.identificador} — {exp.asunto}
              </option>
            ))}
          </select>
        </label>

        <label className="campo">
          <span>Capacidad de adjuntos por fondo</span>
          <select
            value={campos.adjuntos_mb}
            onChange={(e) => actualizar('adjuntos_mb', Number(e.target.value))}
          >
            {CAPACIDADES_ADJUNTOS_MB.map(({ valor, etiqueta }) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </label>

        <div className="rejilla-form">
          <label className="campo">
            <span>Contraseña del Fondo 1 *</span>
            <input
              type="password"
              value={campos.password_visible}
              onChange={(e) => actualizar('password_visible', e.target.value)}
              minLength={8}
              required
            />
          </label>
          <label className="campo">
            <span>Contraseña del Fondo 2 *</span>
            <input
              type="password"
              value={campos.password_confidencial}
              onChange={(e) => actualizar('password_confidencial', e.target.value)}
              minLength={8}
              required
            />
          </label>
        </div>

        <label className="campo">
          <span>Contenido del Fondo 1 (opcional)</span>
          <textarea
            rows={2}
            value={campos.contenido_visible}
            onChange={(e) => actualizar('contenido_visible', e.target.value)}
            placeholder="Se abrirá con la Contraseña del Fondo 1"
          />
        </label>

        <label className="campo">
          <span>Contenido del Fondo 2 (opcional)</span>
          <textarea
            rows={2}
            value={campos.contenido_confidencial}
            onChange={(e) => actualizar('contenido_confidencial', e.target.value)}
            placeholder="Se abrirá con la Contraseña del Fondo 2"
          />
        </label>

        <div className="rejilla-form">
          <label className="campo">
            <span>Archivo del Fondo 1 (opcional)</span>
            <input
              type="file"
              accept={ARCHIVO_ACCEPT}
              onChange={(e) => seleccionarArchivo('visible', e)}
            />
          </label>
          <label className="campo">
            <span>Archivo del Fondo 2 (opcional)</span>
            <input
              type="file"
              accept={ARCHIVO_ACCEPT}
              onChange={(e) => seleccionarArchivo('confidencial', e)}
            />
          </label>
        </div>

        <p className="nota">
          Tipos admitidos: TXT, CSV, PNG, JPG, PDF y ZIP. El servidor valida el contenido real
          con sus <em>magic bytes</em>: una extensión que no corresponde al contenido se
          rechaza y queda registrado como alerta de seguridad.
          <br />
          Los archivos se cifran por fragmentos y se guardan en un archivo de <strong>tamaño
          fijo</strong>: da igual cuántos adjuntos haya o cuánto ocupen, la bóveda ocupa
          siempre los mismos bytes en disco.
        </p>

        <div className="formulario-acciones">
          <button type="button" className="boton" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton-primario" disabled={enviando}>
            {enviando ? 'Creando…' : 'Crear bóveda'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
