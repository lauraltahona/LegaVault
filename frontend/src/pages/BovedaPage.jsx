import { useEffect, useState } from 'react'

import AbrirBovedaModal from '../components/AbrirBovedaModal.jsx'
import Aviso from '../components/Aviso.jsx'
import CrearBovedaModal from '../components/CrearBovedaModal.jsx'
import { eliminarBoveda, listarBovedas } from '../api/bovedas.js'
import { listarExpedientes } from '../api/expedientes.js'
import { useAuth } from '../context/AuthContext.jsx'

function formatearFecha(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-ES')
  } catch {
    return iso
  }
}

export default function BovedaPage() {
  const { usuario, puedeGestionar } = useAuth()
  const [bovedas, setBovedas] = useState([])
  const [expedientes, setExpedientes] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [creando, setCreando] = useState(false)
  const [abriendo, setAbriendo] = useState(null)

  async function cargar() {
    setCargando(true)
    setError('')
    try {
      setBovedas(await listarBovedas())
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargar()
    listarExpedientes().then(setExpedientes).catch(() => setExpedientes([]))
  }, [])

  async function eliminar(boveda) {
    if (!window.confirm(`¿Eliminar la bóveda "${boveda.nombre}"? Esta acción no se puede deshacer.`))
      return
    setError('')
    try {
      await eliminarBoveda(boveda.id)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Bóveda cifrada</h1>
          <p className="subtitulo">
            Contenido protegido con AES-256-GCM. Cada bóveda guarda dos vistas
            independientes: cada contraseña abre su propio contenido.
          </p>
        </div>
        {puedeGestionar && (
          <button type="button" className="boton boton-primario" onClick={() => setCreando(true)}>
            + Nueva bóveda
          </button>
        )}
      </header>

      <Aviso tipo="error">{error}</Aviso>

      {cargando ? (
        <section className="panel">
          <p className="vacio">Cargando…</p>
        </section>
      ) : bovedas.length === 0 ? (
        <section className="panel">
          <p className="vacio">
            No hay bóvedas disponibles. {puedeGestionar ? 'Cree una para empezar.' : ''}
          </p>
        </section>
      ) : (
        <div className="rejilla-dos">
          {bovedas.map((boveda) => (
            <section key={boveda.id} className="panel tarjeta-boveda">
              <div className="panel-cabecera">
                <h2>🔐 {boveda.nombre}</h2>
                <span className="insignia insignia-azul">Cifrada</span>
              </div>
              {boveda.descripcion && <p className="subtexto">{boveda.descripcion}</p>}
              <dl className="lista-datos">
                <div>
                  <dt>Expediente</dt>
                  <dd>{boveda.expediente_identificador || 'Sin expediente'}</dd>
                </div>
                <div>
                  <dt>Actualizada</dt>
                  <dd>{formatearFecha(boveda.actualizado_en)}</dd>
                </div>
              </dl>
              <div className="formulario-acciones">
                {usuario.rol === 'admin' || boveda.creado_por_id === usuario.id ? (
                  <button
                    type="button"
                    className="boton boton-peligro boton-mini"
                    onClick={() => eliminar(boveda)}
                  >
                    Eliminar
                  </button>
                ) : null}
                <button
                  type="button"
                  className="boton boton-primario"
                  onClick={() => setAbriendo(boveda)}
                >
                  Abrir
                </button>
              </div>
            </section>
          ))}
        </div>
      )}

      {creando && (
        <CrearBovedaModal
          expedientes={expedientes}
          onCerrar={() => setCreando(false)}
          onCreada={cargar}
        />
      )}

      {abriendo && (
        <AbrirBovedaModal
          boveda={abriendo}
          onCerrar={() => setAbriendo(null)}
          onCambio={cargar}
        />
      )}
    </div>
  )
}
