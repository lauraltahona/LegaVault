import { useEffect, useState } from 'react'

import Aviso from '../components/Aviso.jsx'
import Insignia from '../components/Insignia.jsx'
import { listarAuditoria, resumenAuditoria, verificarAuditoria } from '../api/auditoria.js'
import { ACCIONES_AUDITORIA, RESULTADOS_AUDITORIA, opciones } from '../constants.js'
import { etiqueta, fechaHora } from '../utils/format.js'

const ENTIDADES = {
  usuario: 'Usuario',
  expediente: 'Expediente',
  documento: 'Documento',
  boveda: 'Bóveda',
}

function tonoResultado(resultado) {
  switch (resultado) {
    case 'ok':
      return 'verde'
    case 'denegado':
      return 'ambar'
    case 'error':
      return 'rojo'
    default:
      return 'neutro'
  }
}

function hashCorto(hash) {
  return hash ? `${hash.slice(0, 10)}…` : '—'
}

export default function AuditoriaPage() {
  const [registros, setRegistros] = useState([])
  const [resumen, setResumen] = useState(null)
  const [verificacion, setVerificacion] = useState(null)
  const [filtros, setFiltros] = useState({ accion: '', resultado: '', usuario: '', entidad: '' })
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)
  const [verificando, setVerificando] = useState(false)

  async function cargar() {
    setCargando(true)
    try {
      const [lista, totales] = await Promise.all([listarAuditoria(filtros), resumenAuditoria()])
      setRegistros(lista)
      setResumen(totales)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    const temporizador = setTimeout(cargar, 250)
    return () => clearTimeout(temporizador)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.accion, filtros.resultado, filtros.usuario, filtros.entidad])

  async function verificar() {
    setVerificando(true)
    try {
      setVerificacion(await verificarAuditoria())
    } catch (err) {
      setError(err.message)
    } finally {
      setVerificando(false)
    }
  }

  const tarjetas = resumen
    ? [
        { etiqueta: 'Registros totales', valor: resumen.total, tono: 'gris' },
        { etiqueta: 'Correctos', valor: resumen.por_resultado?.ok ?? 0, tono: 'verde' },
        { etiqueta: 'Denegados', valor: resumen.por_resultado?.denegado ?? 0, tono: 'ambar' },
        { etiqueta: 'Errores', valor: resumen.por_resultado?.error ?? 0, tono: 'rojo' },
      ]
    : []

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Auditoría</h1>
          <p className="subtitulo">
            Registro local e inalterable de todas las acciones, encadenado con SHA-256.
          </p>
        </div>
        <button type="button" className="boton" onClick={verificar} disabled={verificando}>
          {verificando ? 'Verificando…' : 'Verificar integridad'}
        </button>
      </header>

      <Aviso tipo="error">{error}</Aviso>

      {verificacion && (
        <Aviso tipo={verificacion.integro ? 'ok' : 'error'}>
          {verificacion.integro
            ? `Cadena íntegra: ${verificacion.total} registros verificados correctamente.`
            : `¡ALERTA! La cadena está alterada en el registro #${verificacion.indice_roto}. ` +
              'El archivo de auditoría fue modificado.'}
        </Aviso>
      )}

      <section className="tarjetas">
        {tarjetas.map((tarjeta) => (
          <div key={tarjeta.etiqueta} className={`tarjeta-stat tarjeta-${tarjeta.tono}`}>
            <span className="tarjeta-valor">{tarjeta.valor}</span>
            <span className="tarjeta-etiqueta">{tarjeta.etiqueta}</span>
          </div>
        ))}
      </section>

      <section className="panel">
        <div className="filtros">
          <select
            value={filtros.accion}
            onChange={(e) => setFiltros({ ...filtros, accion: e.target.value })}
          >
            <option value="">Todas las acciones</option>
            {opciones(ACCIONES_AUDITORIA).map(({ valor, etiqueta: nombre }) => (
              <option key={valor} value={valor}>
                {nombre}
              </option>
            ))}
          </select>
          <select
            value={filtros.resultado}
            onChange={(e) => setFiltros({ ...filtros, resultado: e.target.value })}
          >
            <option value="">Todos los resultados</option>
            {opciones(RESULTADOS_AUDITORIA).map(({ valor, etiqueta: nombre }) => (
              <option key={valor} value={valor}>
                {nombre}
              </option>
            ))}
          </select>
          <select
            value={filtros.entidad}
            onChange={(e) => setFiltros({ ...filtros, entidad: e.target.value })}
          >
            <option value="">Todas las entidades</option>
            {opciones(ENTIDADES).map(({ valor, etiqueta: nombre }) => (
              <option key={valor} value={valor}>
                {nombre}
              </option>
            ))}
          </select>
          <input
            type="search"
            placeholder="Usuario…"
            value={filtros.usuario}
            onChange={(e) => setFiltros({ ...filtros, usuario: e.target.value })}
          />
        </div>

        {cargando ? (
          <p className="vacio">Cargando…</p>
        ) : registros.length === 0 ? (
          <p className="vacio">No hay registros que coincidan con los filtros.</p>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Acción</th>
                <th>Resultado</th>
                <th>Usuario</th>
                <th>Entidad</th>
                <th>Detalle</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {registros.map((registro) => (
                <tr key={registro.id}>
                  <td>{fechaHora(registro.creado_en)}</td>
                  <td>{etiqueta(ACCIONES_AUDITORIA, registro.accion)}</td>
                  <td>
                    <Insignia tono={tonoResultado(registro.resultado)}>
                      {etiqueta(RESULTADOS_AUDITORIA, registro.resultado)}
                    </Insignia>
                  </td>
                  <td>{registro.usuario || 'sistema'}</td>
                  <td>{registro.entidad ? etiqueta(ENTIDADES, registro.entidad) : '—'}</td>
                  <td className="celda-detalle">{registro.detalle}</td>
                  <td className="celda-hash" title={registro.hash_actual}>
                    {hashCorto(registro.hash_actual)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
