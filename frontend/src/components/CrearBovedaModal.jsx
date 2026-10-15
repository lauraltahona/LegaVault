import { useState } from 'react'

import Aviso from './Aviso.jsx'
import Modal from './Modal.jsx'
import { crearBoveda } from '../api/bovedas.js'

/**
 * Formulario para crear una bóveda de doble fondo (Módulo 4).
 *
 * Se solicitan **dos contraseñas distintas**: cada una abrirá un contenido
 * independiente. La interfaz no revela en ningún momento cuál es cuál.
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
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  function actualizar(clave, valor) {
    setCampos((previos) => ({ ...previos, [clave]: valor }))
  }

  async function enviar(evento) {
    evento.preventDefault()
    setError('')

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
      await crearBoveda(campos)
      onCreada?.()
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

        <div className="rejilla-form">
          <label className="campo">
            <span>Contraseña 1 *</span>
            <input
              type="password"
              value={campos.password_visible}
              onChange={(e) => actualizar('password_visible', e.target.value)}
              minLength={8}
              required
            />
          </label>
          <label className="campo">
            <span>Contraseña 2 *</span>
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
          <span>Contenido de la bóveda 1 (opcional)</span>
          <textarea
            rows={2}
            value={campos.contenido_visible}
            onChange={(e) => actualizar('contenido_visible', e.target.value)}
            placeholder="Se abrirá con la Contraseña 1"
          />
        </label>

        <label className="campo">
          <span>Contenido de la bóveda 2 (opcional)</span>
          <textarea
            rows={2}
            value={campos.contenido_confidencial}
            onChange={(e) => actualizar('contenido_confidencial', e.target.value)}
            placeholder="Se abrirá con la Contraseña 2"
          />
        </label>

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
