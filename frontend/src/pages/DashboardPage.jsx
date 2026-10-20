import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import Aviso from '../components/Aviso.jsx'
import Insignia, { tonoEstado, tonoSeveridad } from '../components/Insignia.jsx'
import { listarAlertas, resumenAlertas } from '../api/alertas.js'
import { resumenAuditoria } from '../api/auditoria.js'
import { listarBovedas } from '../api/bovedas.js'
import { listarDocumentos } from '../api/documentos.js'
import { listarExpedientes } from '../api/expedientes.js'
import { listarUsuarios } from '../api/usuarios.js'
import { useAuth } from '../context/AuthContext.jsx'
import { ESTADOS_EXPEDIENTE, ROLES, SEVERIDADES, TIPOS_ALERTA } from '../constants.js'
import { fechaHora, etiqueta } from '../utils/format.js'
import { itemsDe } from '../utils/paginacion.js'

export default function DashboardPage() {
  const { usuario, esAdmin } = useAuth()
  const [expedientes, setExpedientes] = useState([])
  const [documentos, setDocumentos] = useState([])
  const [bovedas, setBovedas] = useState([])
  const [resumen, setResumen] = useState(null)
  const [alertas, setAlertas] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [auditoria, setAuditoria] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    async function cargar() {
      try {
        const [exps, docs, bvs] = await Promise.all([
          listarExpedientes(),
          listarDocumentos(),
          listarBovedas(),
        ])
        setExpedientes(itemsDe(exps))
        setDocumentos(itemsDe(docs))
        setBovedas(bvs)
        if (esAdmin) {
          const [res, ultimas, users, audit] = await Promise.all([
            resumenAlertas(),
            listarAlertas({ limite: 5 }),
            listarUsuarios(),
            resumenAuditoria(),
          ])
          setResumen(res)
          setAlertas(ultimas)
          setUsuarios(users)
          setAuditoria(audit)
        }
      } catch (err) {
        setError(err.message)
      }
    }
    cargar()
  }, [esAdmin])

  const tarjetas = [
    { etiqueta: 'Expedientes con acceso', valor: expedientes.length, tono: 'azul' },
    { etiqueta: 'Documentos disponibles', valor: documentos.length, tono: 'verde' },
    { etiqueta: 'Bóvedas cifradas', valor: bovedas.length, tono: 'ambar' },
  ]
  if (esAdmin) {
    tarjetas.push({ etiqueta: 'Usuarios', valor: usuarios.length, tono: 'gris' })
    tarjetas.push({
      etiqueta: 'Alertas sin leer',
      valor: resumen?.no_leidas ?? 0,
      tono: (resumen?.no_leidas ?? 0) > 0 ? 'rojo' : 'gris',
    })
    tarjetas.push({
      etiqueta: 'Registros de auditoría',
      valor: auditoria?.total ?? 0,
      tono: 'gris',
    })
  }

  const recientes = expedientes.slice(0, 6)

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Hola, {usuario?.nombre_completo?.split(' ')[0]}</h1>
          <p className="subtitulo">
            Rol: {etiqueta(ROLES, usuario?.rol)} · Último acceso: {fechaHora(usuario?.ultimo_acceso)}
          </p>
        </div>
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

      <div className="rejilla-dos">
        <section className="panel">
          <div className="panel-cabecera">
            <h2>Expedientes recientes</h2>
            <Link className="enlace" to="/expedientes">
              Ver todos
            </Link>
          </div>
          {recientes.length === 0 ? (
            <p className="vacio">Todavía no hay expedientes a los que tenga acceso.</p>
          ) : (
            <table className="tabla">
              <thead>
                <tr>
                  <th>Identificador</th>
                  <th>Asunto</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {recientes.map((exp) => (
                  <tr key={exp.id}>
                    <td>
                      <Link className="enlace" to={`/expedientes/${exp.id}`}>
                        {exp.identificador}
                      </Link>
                    </td>
                    <td>{exp.asunto}</td>
                    <td>
                      <Insignia tono={tonoEstado(exp.estado)}>
                        {etiqueta(ESTADOS_EXPEDIENTE, exp.estado)}
                      </Insignia>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {esAdmin && (
          <section className="panel">
            <div className="panel-cabecera">
              <h2>Alertas recientes</h2>
              <Link className="enlace" to="/alertas">
                Ver todas
              </Link>
            </div>
            {alertas.length === 0 ? (
              <p className="vacio">Sin eventos de seguridad registrados.</p>
            ) : (
              <ul className="lista-eventos">
                {alertas.map((alerta) => (
                  <li key={alerta.id}>
                    <Insignia tono={tonoSeveridad(alerta.severidad)}>
                      {etiqueta(SEVERIDADES, alerta.severidad)}
                    </Insignia>
                    <div>
                      <strong>{etiqueta(TIPOS_ALERTA, alerta.tipo)}</strong>
                      <small>
                        {alerta.usuario || 'sistema'} · {fechaHora(alerta.creado_en)}
                      </small>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    </div>
  )
}
