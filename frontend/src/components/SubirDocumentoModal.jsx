import { useState } from 'react'

import Aviso from './Aviso.jsx'
import Modal from './Modal.jsx'
import { cargarDocumento } from '../api/documentos.js'
import { useAuth } from '../context/AuthContext.jsx'
import {
  ARCHIVO_ACCEPT,
  EXTENSIONES_ARCHIVO_PERMITIDAS,
  NIVELES_SENSIBILIDAD,
  TIPOS_DOCUMENTO,
  opciones,
} from '../constants.js'

/** Devuelve la extensión en minúsculas de un nombre de archivo ('' si no tiene). */
function extensionDe(nombre) {
  const punto = String(nombre ?? '').lastIndexOf('.')
  return punto === -1 ? '' : String(nombre).slice(punto).toLowerCase()
}

/** Formulario modal para subir un documento a un expediente (Módulo 3). */
export default function SubirDocumentoModal({
  expedienteId,
  expedientes,
  onCerrar,
  onSubido,
}) {
  const { usuario } = useAuth()
  const esAsistente = usuario?.rol === 'asistente'
  const niveles = esAsistente
    ? opciones(NIVELES_SENSIBILIDAD).filter(({ valor }) => valor !== 'confidencial')
    : opciones(NIVELES_SENSIBILIDAD)
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

  /** Pre-chequeo de la lista blanca (el servidor re-valida por magic bytes). */
  function seleccionarArchivo(evento) {
    const elegido = evento.target.files?.[0] ?? null
    setError('')
    if (!elegido) {
      setArchivo(null)
      return
    }
    const extension = extensionDe(elegido.name)
    if (!EXTENSIONES_ARCHIVO_PERMITIDAS.includes(extension)) {
      setArchivo(null)
      evento.target.value = ''
      setError(
        `Tipo de archivo no permitido ('${extension || 'sin extensión'}'). ` +
          `Extensiones admitidas: ${EXTENSIONES_ARCHIVO_PERMITIDAS.join(', ')}. ` +
          'El contenido se verifica en el servidor con sus magic bytes: la extensión no puede mentir.',
      )
      return
    }
    setArchivo(elegido)
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
              {niveles.map(({ valor, etiqueta }) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="campo">
          <span>Archivo *</span>
          <input
            type="file"
            accept={ARCHIVO_ACCEPT}
            onChange={seleccionarArchivo}
          />
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
          Tipos admitidos: TXT, CSV, PNG, JPG, PDF y ZIP. El servidor valida el contenido
          real con sus <em>magic bytes</em>: una extensión que no corresponde al contenido
          se rechaza y queda registrado como alerta de seguridad.
          <br />
          {esAsistente
            ? 'Como asistente jurídico solo puede cargar documentos públicos o internos; los confidenciales los gestiona un abogado o un administrador.'
            : 'Los documentos marcados como confidencial no estarán disponibles para el rol de asistente jurídico.'}
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
