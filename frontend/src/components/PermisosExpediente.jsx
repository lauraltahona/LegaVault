import { useEffect, useState } from 'react'

import Aviso from './Aviso.jsx'
import { actualizarPermisos } from '../api/expedientes.js'
import { listarSeleccionUsuarios } from '../api/usuarios.js'
import { ACCIONES_PERMISO } from '../constants.js'

// Valores por defecto (equivalentes a los del backend) para un usuario autorizado.
const DEFAULTS = {
  leer: true,
  cargar: true,
  descargar: true,
  editar: false,
  eliminar: false,
}

const ACCIONES = Object.keys(ACCIONES_PERMISO)

// Sección de administración de la matriz de permisos por expediente (Módulo 5).
// Solo se muestra al administrador o al abogado responsable.
export default function PermisosExpediente({ expediente, onActualizado }) {
  const [usuarios, setUsuarios] = useState({})
  const [matriz, setMatriz] = useState({})
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  const autorizados = expediente.usuarios_autorizados ?? []
  const responsableId = expediente.abogado_responsable_id

  useEffect(() => {
    let activo = true
    listarSeleccionUsuarios()
      .then((lista) => {
        if (!activo) return
        setUsuarios(Object.fromEntries(lista.map((u) => [u.id, u.nombre_completo])))
      })
      .catch(() => {
        if (activo) setUsuarios({})
      })
    return () => {
      activo = false
    }
  }, [])

  useEffect(() => {
    const siguiente = {}
    for (const uid of autorizados) {
      siguiente[uid] = { ...DEFAULTS, ...(expediente.permisos?.[uid] ?? {}) }
    }
    setMatriz(siguiente)
  }, [expediente])

  function alternar(uid, accion) {
    setMensaje('')
    setMatriz((actual) => ({
      ...actual,
      [uid]: { ...actual[uid], [accion]: !actual[uid][accion] },
    }))
  }

  async function guardar() {
    setError('')
    setMensaje('')
    setGuardando(true)
    try {
      const actualizado = await actualizarPermisos(expediente.id, matriz)
      onActualizado(actualizado)
      setMensaje('Permisos guardados correctamente.')
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-cabecera">
        <h2>Permisos por usuario</h2>
        <button
          type="button"
          className="boton boton-primario"
          onClick={guardar}
          disabled={guardando}
        >
          {guardando ? 'Guardando…' : 'Guardar permisos'}
        </button>
      </div>

      <Aviso tipo="error">{error}</Aviso>
      {mensaje && <Aviso tipo="ok">{mensaje}</Aviso>}

      <p className="nota">
        El administrador y el abogado responsable conservan siempre el control total. La matriz
        refina las acciones del resto de usuarios autorizados (por defecto pueden leer, cargar y
        descargar).
      </p>

      {autorizados.length === 0 ? (
        <p>No hay usuarios autorizados además del responsable.</p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Usuario</th>
              {ACCIONES.map((accion) => (
                <th key={accion}>{ACCIONES_PERMISO[accion]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {autorizados.map((uid) => (
              <tr key={uid}>
                <td>{usuarios[uid] ?? uid}</td>
                {ACCIONES.map((accion) => (
                  <td key={accion}>
                    <input
                      type="checkbox"
                      aria-label={`${ACCIONES_PERMISO[accion]} para ${usuarios[uid] ?? uid}`}
                      checked={Boolean(matriz[uid]?.[accion])}
                      onChange={() => alternar(uid, accion)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {responsableId && (
        <p className="nota">
          Responsable: {usuarios[responsableId] ?? responsableId} (control total).
        </p>
      )}
    </section>
  )
}
