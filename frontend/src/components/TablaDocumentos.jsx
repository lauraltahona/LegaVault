import { useState } from 'react'

import Insignia, { tonoSensibilidad } from './Insignia.jsx'
import { NIVELES_SENSIBILIDAD, TIPOS_DOCUMENTO } from '../constants.js'
import { verificarIntegridad } from '../api/documentos.js'
import { etiqueta, fecha, tamanoArchivo } from '../utils/format.js'

/**
 * Tabla reutilizable de documentos (Módulo 3).
 *
 * Incluye el botón "Verificar integridad": llama al backend, que recalcula el
 * SHA-256 del archivo en disco y lo compara con el metadato registrado. El
 * resultado se muestra bajo los botones de cada fila.
 */
export default function TablaDocumentos({
  documentos,
  onDescargar,
  onEliminar,
  puedeEliminar,
  expedientesPorId,
}) {
  // Estado de verificación por documento: { [id]: { estado, mensaje } }
  const [verificaciones, setVerificaciones] = useState({})

  if (documentos.length === 0) {
    return <p className="vacio">No hay documentos que mostrar.</p>
  }

  async function verificar(documento) {
    setVerificaciones((prev) => ({
      ...prev,
      [documento.id]: { estado: 'comprobando', mensaje: '' },
    }))
    try {
      const resultado = await verificarIntegridad(documento.id)
      setVerificaciones((prev) => ({
        ...prev,
        [documento.id]: {
          estado: resultado.integro ? 'integro' : 'roto',
          mensaje: resultado.mensaje,
        },
      }))
    } catch (err) {
      setVerificaciones((prev) => ({
        ...prev,
        [documento.id]: { estado: 'error', mensaje: err.message },
      }))
    }
  }

  return (
    <table className="tabla">
      <thead>
        <tr>
          <th>Nombre</th>
          {expedientesPorId && <th>Expediente</th>}
          <th>Tipo</th>
          <th>Sensibilidad</th>
          <th>Tamaño</th>
          <th>Cargado</th>
          <th aria-label="Acciones" />
        </tr>
      </thead>
      <tbody>
        {documentos.map((documento) => {
          const verificacion = verificaciones[documento.id]
          const comprobando = verificacion?.estado === 'comprobando'

          return (
            <tr key={documento.id}>
              <td>
                <strong>{documento.nombre_original}</strong>
                {documento.descripcion && <small className="subtexto">{documento.descripcion}</small>}
              </td>
              {expedientesPorId && (
                <td>{expedientesPorId[documento.expediente_id]?.identificador ?? '—'}</td>
              )}
              <td>{etiqueta(TIPOS_DOCUMENTO, documento.tipo)}</td>
              <td>
                <Insignia tono={tonoSensibilidad(documento.nivel_sensibilidad)}>
                  {etiqueta(NIVELES_SENSIBILIDAD, documento.nivel_sensibilidad)}
                </Insignia>
              </td>
              <td>{tamanoArchivo(documento.tamano_bytes)}</td>
              <td>{fecha(documento.creado_en)}</td>
              <td className="acciones">
                <button
                  type="button"
                  className="boton boton-mini"
                  onClick={() => onDescargar(documento)}
                >
                  Descargar
                </button>
                <button
                  type="button"
                  className="boton boton-mini"
                  title="Re-verificar el SHA-256 del archivo en disco"
                  aria-label={`Verificar integridad de ${documento.nombre_original}`}
                  disabled={comprobando}
                  onClick={() => verificar(documento)}
                >
                  {comprobando ? 'Verificando…' : 'Verificar'}
                </button>
                {puedeEliminar?.(documento) && (
                  <button
                    type="button"
                    className="boton boton-mini boton-peligro"
                    onClick={() => onEliminar(documento)}
                  >
                    Eliminar
                  </button>
                )}
                {verificacion && (
                  <small
                    className={`verificacion verificacion-${verificacion.estado}`}
                    role="status"
                  >
                    {verificacion.estado === 'integro' && '✅ '}
                    {verificacion.estado === 'roto' && '❌ '}
                    {verificacion.estado === 'error' && '⚠️ '}
                    {verificacion.mensaje}
                  </small>
                )}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
