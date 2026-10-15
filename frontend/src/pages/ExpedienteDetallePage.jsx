import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import Aviso from '../components/Aviso.jsx'
import Insignia, { tonoEstado } from '../components/Insignia.jsx'
import PermisosExpediente from '../components/PermisosExpediente.jsx'
import SubirDocumentoModal from '../components/SubirDocumentoModal.jsx'
import TablaDocumentos from '../components/TablaDocumentos.jsx'
import { descargarDocumento, eliminarDocumento, listarDocumentos } from '../api/documentos.js'
import { obtenerExpediente } from '../api/expedientes.js'
import { useAuth } from '../context/AuthContext.jsx'
import { ESTADOS_EXPEDIENTE, TIPOS_PROCESO } from '../constants.js'
import { etiqueta, fechaHora } from '../utils/format.js'

export default function ExpedienteDetallePage() {
  const { id } = useParams()
  const { usuario, puedeCargar } = useAuth()
  const [expediente, setExpediente] = useState(null)
  const [documentos, setDocumentos] = useState([])
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  async function cargar() {
    setCargando(true)
    try {
      const [exp, docs] = await Promise.all([
        obtenerExpediente(id),
        listarDocumentos({ expediente_id: id }),
      ])
      setExpediente(exp)
      setDocumentos(docs)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function descargar(documento) {
    setError('')
    try {
      await descargarDocumento(documento.id, documento.nombre_original)
    } catch (err) {
      setError(err.message)
    }
  }

  async function eliminar(documento) {
    if (!window.confirm(`¿Eliminar el documento "${documento.nombre_original}"?`)) return
    setError('')
    try {
      await eliminarDocumento(documento.id)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  if (cargando) return <div className="pagina">Cargando…</div>

  if (!expediente) {
    return (
      <div className="pagina">
        <Aviso tipo="error">{error || 'No se pudo cargar el expediente.'}</Aviso>
        <Link className="enlace" to="/expedientes">
          ← Volver a expedientes
        </Link>
      </div>
    )
  }

  const esResponsable = expediente.abogado_responsable_id === usuario.id
  const puedeGestionarExp = usuario.rol === 'admin' || esResponsable
  const permisosPropios = expediente.permisos?.[usuario.id] ?? {}
  const permisoEliminar = permisosPropios.eliminar === true
  const puedeCargarAqui = puedeCargar && permisosPropios.cargar !== false
  const puedeBorrarDocumento = (documento) =>
    usuario.rol === 'admin' ||
    esResponsable ||
    permisoEliminar ||
    documento.subido_por_id === usuario.id

  return (
    <div className="pagina">
      <Link className="enlace" to="/expedientes">
        ← Volver a expedientes
      </Link>

      <header className="pagina-cabecera">
        <div>
          <h1>{expediente.identificador}</h1>
          <p className="subtitulo">{expediente.asunto}</p>
        </div>
        <Insignia tono={tonoEstado(expediente.estado)}>
          {etiqueta(ESTADOS_EXPEDIENTE, expediente.estado)}
        </Insignia>
      </header>

      <Aviso tipo="error">{error}</Aviso>

      <section className="panel datos-expediente">
        <dl className="lista-datos">
          <div>
            <dt>Cliente</dt>
            <dd>{expediente.cliente}</dd>
          </div>
          <div>
            <dt>Tipo de proceso</dt>
            <dd>{etiqueta(TIPOS_PROCESO, expediente.tipo_proceso)}</dd>
          </div>
          <div>
            <dt>Abogado responsable</dt>
            <dd>{expediente.abogado_responsable_nombre ?? '—'}</dd>
          </div>
          <div>
            <dt>Creado</dt>
            <dd>{fechaHora(expediente.creado_en)}</dd>
          </div>
          <div className="ancho-completo">
            <dt>Descripción</dt>
            <dd>{expediente.descripcion || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="panel">
        <div className="panel-cabecera">
          <h2>Documentos ({documentos.length})</h2>
          {puedeCargarAqui && (
            <button type="button" className="boton boton-primario" onClick={() => setSubiendo(true)}>
              + Cargar documento
            </button>
          )}
        </div>
        <TablaDocumentos
          documentos={documentos}
          onDescargar={descargar}
          onEliminar={eliminar}
          puedeEliminar={puedeBorrarDocumento}
        />
      </section>

      {puedeGestionarExp && (
        <PermisosExpediente expediente={expediente} onActualizado={setExpediente} />
      )}

      {subiendo && (
        <SubirDocumentoModal
          expedienteId={expediente.id}
          expedientes={[]}
          onCerrar={() => setSubiendo(false)}
          onSubido={cargar}
        />
      )}
    </div>
  )
}
