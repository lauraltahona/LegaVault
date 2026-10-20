import { useEffect, useMemo, useState } from 'react'

import Aviso from '../components/Aviso.jsx'
import Paginacion from '../components/Paginacion.jsx'
import SubirDocumentoModal from '../components/SubirDocumentoModal.jsx'
import TablaDocumentos from '../components/TablaDocumentos.jsx'
import { descargarDocumento, eliminarDocumento, listarDocumentos } from '../api/documentos.js'
import { listarExpedientes } from '../api/expedientes.js'
import { useAuth } from '../context/AuthContext.jsx'
import {
  NIVELES_SENSIBILIDAD,
  TIPOS_DOCUMENTO,
  opciones,
} from '../constants.js'

export default function DocumentosPage() {
  const { usuario, puedeCargar } = useAuth()
  const [documentos, setDocumentos] = useState([])
  const [expedientes, setExpedientes] = useState([])
  const [filtros, setFiltros] = useState({ q: '', expediente_id: '', tipo: '', nivel_sensibilidad: '' })
  const [pagina, setPagina] = useState(1)
  const [paginacion, setPaginacion] = useState({ total: 0, paginas: 0, porPagina: 20 })
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  const expedientesPorId = useMemo(
    () => Object.fromEntries(expedientes.map((exp) => [exp.id, exp])),
    [expedientes],
  )

  async function cargar() {
    setCargando(true)
    try {
      const respuesta = await listarDocumentos({ ...filtros, pagina, por_pagina: paginacion.porPagina })
      if (Array.isArray(respuesta)) {
        setDocumentos(respuesta)
        setPaginacion((prev) => ({ ...prev, total: respuesta.length, paginas: 1 }))
      } else if (respuesta && Array.isArray(respuesta.items)) {
        setDocumentos(respuesta.items)
        setPaginacion({
          total: respuesta.total || 0,
          paginas: respuesta.paginas || 0,
          porPagina: respuesta.por_pagina || paginacion.porPagina,
        })
      } else {
        setDocumentos([])
        setPaginacion((prev) => ({ ...prev, total: 0, paginas: 0 }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    listarExpedientes().then((resp) => {
      if (Array.isArray(resp)) setExpedientes(resp)
      else if (resp && Array.isArray(resp.items)) setExpedientes(resp.items)
      else setExpedientes([])
    }).catch(() => setExpedientes([]))
  }, [])

  useEffect(() => {
    setPagina(1)
  }, [filtros.q, filtros.expediente_id, filtros.tipo, filtros.nivel_sensibilidad])

  useEffect(() => {
    const temporizador = setTimeout(cargar, 250)
    return () => clearTimeout(temporizador)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.q, filtros.expediente_id, filtros.tipo, filtros.nivel_sensibilidad, pagina])

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

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Documentos</h1>
          <p className="subtitulo">
            Busque por nombre, categoría o expediente. Solo se muestran los documentos autorizados.
          </p>
        </div>
        {puedeCargar && (
          <button type="button" className="boton boton-primario" onClick={() => setSubiendo(true)}>
            + Cargar documento
          </button>
        )}
      </header>

      <Aviso tipo="error">{error}</Aviso>

      <section className="panel">
        <div className="filtros">
          <input
            type="search"
            placeholder="Buscar por nombre…"
            value={filtros.q}
            onChange={(e) => setFiltros({ ...filtros, q: e.target.value })}
          />
          <select
            value={filtros.expediente_id}
            onChange={(e) => setFiltros({ ...filtros, expediente_id: e.target.value })}
          >
            <option value="">Todos los expedientes</option>
            {expedientes.map((exp) => (
              <option key={exp.id} value={exp.id}>
                {exp.identificador}
              </option>
            ))}
          </select>
          <select
            value={filtros.tipo}
            onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}
          >
            <option value="">Todas las categorías</option>
            {opciones(TIPOS_DOCUMENTO).map(({ valor, etiqueta }) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
          <select
            value={filtros.nivel_sensibilidad}
            onChange={(e) => setFiltros({ ...filtros, nivel_sensibilidad: e.target.value })}
          >
            <option value="">Toda sensibilidad</option>
            {opciones(NIVELES_SENSIBILIDAD).map(({ valor, etiqueta }) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
        </div>

        {cargando ? (
          <p className="vacio">Cargando…</p>
        ) : (
          <TablaDocumentos
            documentos={documentos}
            expedientesPorId={expedientesPorId}
            onDescargar={descargar}
            onEliminar={eliminar}
            puedeEliminar={(documento) => usuario.rol === 'admin' || documento.subido_por_id === usuario.id}
          />
        )}
      </section>

      {subiendo && (
        <SubirDocumentoModal
          expedientes={expedientes}
          onCerrar={() => setSubiendo(false)}
          onSubido={cargar}
        />
      )}
    </div>
  )
}
