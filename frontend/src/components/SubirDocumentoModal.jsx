import { useState } from 'react'

import Aviso from './Aviso.jsx'
import Modal from './Modal.jsx'
import { cargarDocumento } from '../api/documentos.js'
import { NIVELES_SENSIBILIDAD, TIPOS_DOCUMENTO, opciones } from '../constants.js'

/** Formulario modal para subir un documento a un expediente (Módulo 3). */
export default function SubirDocumentoModal({
  expedienteId,
  expedientes,
  onCerrar,
  onSubido,
}) {
  const [campos, setCampos] = useState({
    expediente_id: expedienteId ?? '',
    tipo: 'contrato',
    nivel_sensibilidad: 'interno',
    descripcion: '',
  })
  const [archivo, setArchivo] = useState(null)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setError('')
    if (!archivo) {
      setError('Debe seleccionar un archivo.')
      return
    }
    setEnviando(true)
    try {
      await cargarDocumento(
        campos.expediente_id,
        campos.tipo,
        campos.nivel_sensibilidad,
        campos.descripcion,
        archivo,
      )
      onSubido?.()
      onCerrar()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal titulo="Cargar documento" onCerrar={onCerrar}>
      <form className="formulario" onSubmit={enviar}>
        <Aviso tipo="error">{error}</Aviso>

        {expedienteId ? (
          <input type="hidden" value={expedienteId} readOnly />
        ) : (
          <label className="campo">
            <span>Expediente *</span>
            <select
              value={campos.expediente_id}
              onChange={(e) => setCampos({ ...campos, expediente_id: e.target.value })}
              required
            >
              <option value="">Seleccione un expediente…</option>
              {expedientes.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {exp.identificador} — {exp.asunto}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className="rejilla-form">
          <label className="campo">
            <span>Tipo *</span>
            <select
              value={campos.tipo}
              onChange={(e) => setCampos({ ...campos, tipo: e.target.value })}
            >
              {opciones(TIPOS_DOCUMENTO).map(({ valor, etiqueta }) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span>Nivel de sensibilidad *</span>
            <select
              value={campos.nivel_sensibilidad}
              onChange={(e) => setCampos({ ...campos, nivel_sensibilidad: e.target.value })}
            >
              {opciones(NIVELES_SENSIBILIDAD).map(({ valor, etiqueta }) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="campo">
          <span>Archivo *</span>
          <input type="file" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
        </label>

        <label className="campo">
          <span>Descripción</span>
          <textarea
            rows={2}
            value={campos.descripcion}
            onChange={(e) => setCampos({ ...campos, descripcion: e.target.value })}
          />
        </label>

        <p className="nota">
          Los documentos marcados como <strong>confidencial</strong> no estarán disponibles para el
          rol de asistente jurídico.
        </p>

        <div className="formulario-acciones">
          <button type="button" className="boton" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton-primario" disabled={enviando}>
            {enviando ? 'Cargando…' : 'Cargar documento'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
