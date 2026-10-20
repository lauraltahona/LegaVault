import { useEffect, useState } from 'react'

import Aviso from '../components/Aviso.jsx'
import Insignia, { tonoSeveridad } from '../components/Insignia.jsx'
import Paginacion from '../components/Paginacion.jsx'
import { listarAlertas, marcarAlertaLeida, marcarTodasLeidas, resumenAlertas } from '../api/alertas.js'
import { SEVERIDADES, TIPOS_ALERTA, opciones } from '../constants.js'
import { fechaHora, etiqueta } from '../utils/format.js'
import { itemsDe } from '../utils/paginacion.js'

export default function AlertasPage() {
  const [alertas, setAlertas] = useState([])
  const [resumen, setResumen] = useState(null)
  const [filtros, setFiltros] = useState({
    tipo: '',
    severidad: '',
    usuario: '',
    solo_no_leidas: false,
  })
  const [pagina, setPagina] = useState(1)
  const [paginacion, setPaginacion] = useState({ total: 0, paginas: 0, porPagina: 20 })
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  async function cargar() {
    setCargando(true)
    try {
      const [respuesta, totales] = await Promise.all([
        listarAlertas({ ...filtros, pagina, por_pagina: paginacion.porPagina }),
        resumenAlertas(),
      ])
      const items = itemsDe(respuesta)
      setAlertas(items)
      setPaginacion((prev) =>
        Array.isArray(respuesta)
          ? { ...prev, total: items.length, paginas: 1 }
          : {
              total: respuesta?.total ?? 0,
              paginas: respuesta?.paginas ?? 0,
              porPagina: respuesta?.por_pagina || prev.porPagina,
            },
      )
      setResumen(totales)
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    setPagina(1)
  }, [filtros.tipo, filtros.severidad, filtros.usuario, filtros.solo_no_leidas])

  useEffect(() => {
    const temporizador = setTimeout(cargar, 250)
    return () => clearTimeout(temporizador)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.tipo, filtros.severidad, filtros.usuario, filtros.solo_no_leidas, pagina])

  async function alternarLeida(alerta) {
    try {
      await marcarAlertaLeida(alerta.id, !alerta.leida)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  async function marcarTodas() {
    try {
      await marcarTodasLeidas()
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  const tarjetas = resumen
    ? [
        { etiqueta: 'Total de eventos', valor: resumen.total, tono: 'gris' },
        { etiqueta: 'Sin leer', valor: resumen.no_leidas, tono: resumen.no_leidas ? 'rojo' : 'gris' },
        { etiqueta: 'Críticas', valor: resumen.por_severidad?.critica ?? 0, tono: 'rojo' },
        { etiqueta: 'Advertencias', valor: resumen.por_severidad?.advertencia ?? 0, tono: 'ambar' },
      ]
    : []

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Alertas de seguridad</h1>
          <p className="subtitulo">
            Eventos de autenticación, bloqueos y accesos denegados. No contienen contraseñas.
          </p>
        </div>
        <button type="button" className="boton" onClick={marcarTodas}>
          Marcar todas como leídas
        </button>
      </header>

      <Aviso tipo="error">{error}</Aviso>

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
          <select value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}>
            <option value="">Todos los eventos</option>
            {opciones(TIPOS_ALERTA).map(({ valor, etiqueta: nombre }) => (
              <option key={valor} value={valor}>
                {nombre}
              </option>
            ))}
          </select>
          <select
            value={filtros.severidad}
            onChange={(e) => setFiltros({ ...filtros, severidad: e.target.value })}
          >
            <option value="">Todas las severidades</option>
            {opciones(SEVERIDADES).map(({ valor, etiqueta: nombre }) => (
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
          <label className="check-inline">
            <input
              type="checkbox"
              checked={filtros.solo_no_leidas}
              onChange={(e) => setFiltros({ ...filtros, solo_no_leidas: e.target.checked })}
            />
            Solo sin leer
          </label>
        </div>

        {cargando ? (
          <p className="vacio">Cargando…</p>
        ) : alertas.length === 0 ? (
          <p className="vacio">No hay alertas que coincidan con los filtros.</p>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Evento</th>
                <th>Severidad</th>
                <th>Usuario</th>
                <th>Detalle</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {alertas.map((alerta) => (
                <tr key={alerta.id} className={alerta.leida ? '' : 'fila-no-leida'}>
                  <td>{fechaHora(alerta.creado_en)}</td>
                  <td>{etiqueta(TIPOS_ALERTA, alerta.tipo)}</td>
                  <td>
                    <Insignia tono={tonoSeveridad(alerta.severidad)}>
                      {etiqueta(SEVERIDADES, alerta.severidad)}
                    </Insignia>
                  </td>
                  <td>{alerta.usuario || '—'}</td>
                  <td className="celda-detalle">{alerta.mensaje}</td>
                  <td className="acciones">
                    <button
                      type="button"
                      className="boton boton-mini"
                      onClick={() => alternarLeida(alerta)}
                    >
                      {alerta.leida ? 'Marcar no leída' : 'Marcar leída'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!cargando && alertas.length > 0 && (
          <Paginacion
            pagina={pagina}
            porPagina={paginacion.porPagina}
            total={paginacion.total}
            paginas={paginacion.paginas}
            onPaginaCambio={setPagina}
          />
        )}
      </section>
    </div>
  )
}
