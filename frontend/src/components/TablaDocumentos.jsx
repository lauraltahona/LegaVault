import Insignia, { tonoSensibilidad } from './Insignia.jsx'
import { NIVELES_SENSIBILIDAD, TIPOS_DOCUMENTO } from '../constants.js'
import { etiqueta, fecha, tamanoArchivo } from '../utils/format.js'

/** Tabla reutilizable de documentos (Módulo 3). */
export default function TablaDocumentos({
  documentos,
  onDescargar,
  onEliminar,
  puedeEliminar,
  expedientesPorId,
}) {
  if (documentos.length === 0) {
    return <p className="vacio">No hay documentos que mostrar.</p>
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
        {documentos.map((documento) => (
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
              {puedeEliminar?.(documento) && (
                <button
                  type="button"
                  className="boton boton-mini boton-peligro"
                  onClick={() => onEliminar(documento)}
                >
                  Eliminar
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
