import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import Aviso from '../components/Aviso.jsx'
import Insignia, { tonoEstado } from '../components/Insignia.jsx'
import Modal from '../components/Modal.jsx'
import {
  actualizarExpediente,
  archivarExpediente,
  crearExpediente,
  listarExpedientes,
} from '../api/expedientes.js'
import { listarSeleccionUsuarios } from '../api/usuarios.js'
import { useAuth } from '../context/AuthContext.jsx'
import { ESTADOS_EXPEDIENTE, TIPOS_PROCESO, opciones } from '../constants.js'
import { fecha, etiqueta } from '../utils/format.js'

const FORMULARIO_VACIO = {
  identificador: '',
  asunto: '',
  cliente: '',
  tipo_proceso: 'civil',
  estado: 'abierto',
  abogado_responsable_id: '',
  descripcion: '',
  usuarios_autorizados: [],
}

export default function ExpedientesPage() {
  const { usuario, puedeGestionar, esAdmin } = useAuth()
  const [expedientes, setExpedientes] = useState([])
  const [personas, setPersonas] = useState([])
  const [filtros, setFiltros] = useState({ q: '', estado: '', tipo_proceso: '' })
  const [formulario, setFormulario] = useState(null)
  const [editandoId, setEditandoId] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  const abogados = useMemo(
    () => personas.filter((persona) => persona.rol === 'abogado' || persona.rol === 'admin'),
    [personas],
  )

  async function cargar() {
    setCargando(true)
    try {
      setExpedientes(await listarExpedientes(filtros))
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    listarSeleccionUsuarios().then(setPersonas).catch(() => setPersonas([]))
  }, [])

  useEffect(() => {
    const temporizador = setTimeout(cargar, 250)
    return () => clearTimeout(temporizador)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.q, filtros.estado, filtros.tipo_proceso])

  function abrirCrear() {
    setError('')
    setEditandoId(null)
    setFormulario({ ...FORMULARIO_VACIO, abogado_responsable_id: usuario.id })
  }

  function abrirEditar(exp) {
    setError('')
    setEditandoId(exp.id)
    setFormulario({
      identificador: exp.identificador,
      asunto: exp.asunto,
      cliente: exp.cliente,
      tipo_proceso: exp.tipo_proceso,
      estado: exp.estado,
      abogado_responsable_id: exp.abogado_responsable_id,
      descripcion: exp.descripcion,
      usuarios_autorizados: exp.usuarios_autorizados,
    })
  }

  async function guardar(evento) {
    evento.preventDefault()
    setError('')
    try {
      if (editandoId) {
        await actualizarExpediente(editandoId, formulario)
      } else {
        await crearExpediente(formulario)
      }
      setFormulario(null)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  async function archivar(exp) {
    if (!window.confirm(`¿Archivar el expediente ${exp.identificador}?`)) return
    try {
      await archivarExpediente(exp.id)
      await cargar()
    } catch (err) {
      setError(err.message)
    }
  }

  function alternarAutorizado(id) {
    setFormulario((previo) => {
      const incluidos = previo.usuarios_autorizados.includes(id)
      return {
        ...previo,
        usuarios_autorizados: incluidos
          ? previo.usuarios_autorizados.filter((valor) => valor !== id)
          : [...previo.usuarios_autorizados, id],
      }
    })
  }

  return (
    <div className="pagina">
      <header className="pagina-cabecera">
        <div>
          <h1>Expedientes</h1>
          <p className="subtitulo">Casos a los que tiene acceso según sus permisos.</p>
        </div>
        {puedeGestionar && (
          <button type="button" className="boton boton-primario" onClick={abrirCrear}>
            + Nuevo expediente
          </button>
        )}
      </header>

      <Aviso tipo="error">{error}</Aviso>

      <section className="panel">
        <div className="filtros">
          <input
            type="search"
            placeholder="Buscar por identificador, asunto o cliente…"
            value={filtros.q}
            onChange={(e) => setFiltros({ ...filtros, q: e.target.value })}
          />
          <select
            value={filtros.estado}
            onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
          >
            <option value="">Todos los estados</option>
            {opciones(ESTADOS_EXPEDIENTE).map(({ valor, etiqueta: nombre }) => (
              <option key={valor} value={valor}>
                {nombre}
              </option>
            ))}
          </select>
          <select
            value={filtros.tipo_proceso}
            onChange={(e) => setFiltros({ ...filtros, tipo_proceso: e.target.value })}
          >
            <option value="">Todos los tipos</option>
            {opciones(TIPOS_PROCESO).map(({ valor, etiqueta: nombre }) => (
              <option key={valor} value={valor}>
                {nombre}
              </option>
            ))}
          </select>
        </div>

        {cargando ? (
          <p className="vacio">Cargando…</p>
        ) : expedientes.length === 0 ? (
          <p className="vacio">No se encontraron expedientes.</p>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Identificador</th>
                <th>Asunto</th>
                <th>Cliente</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Responsable</th>
                <th>Docs.</th>
                <th>Actualizado</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {expedientes.map((exp) => (
                <tr key={exp.id}>
                  <td>
                    <Link className="enlace" to={`/expedientes/${exp.id}`}>
                      {exp.identificador}
                    </Link>
                  </td>
                  <td>{exp.asunto}</td>
                  <td>{exp.cliente}</td>
                  <td>{etiqueta(TIPOS_PROCESO, exp.tipo_proceso)}</td>
                  <td>
                    <Insignia tono={tonoEstado(exp.estado)}>
                      {etiqueta(ESTADOS_EXPEDIENTE, exp.estado)}
                    </Insignia>
                  </td>
                  <td>{exp.abogado_responsable_nombre ?? '—'}</td>
                  <td>{exp.total_documentos ?? 0}</td>
                  <td>{fecha(exp.actualizado_en)}</td>
                  <td className="acciones">
                    {puedeGestionar && (
                      <button type="button" className="boton boton-mini" onClick={() => abrirEditar(exp)}>
                        Editar
                      </button>
                    )}
                    {puedeGestionar && exp.estado !== 'archivado' && (
                      <button
                        type="button"
                        className="boton boton-mini boton-peligro"
                        onClick={() => archivar(exp)}
                      >
                        Archivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {formulario && (
        <Modal
          titulo={editandoId ? 'Editar expediente' : 'Nuevo expediente'}
          onCerrar={() => setFormulario(null)}
          ancho="640px"
        >
          <form className="formulario" onSubmit={guardar}>
            <div className="rejilla-form">
              <label className="campo">
                <span>Identificador *</span>
                <input
                  value={formulario.identificador}
                  onChange={(e) => setFormulario({ ...formulario, identificador: e.target.value })}
                  placeholder="EXP-2026-001"
                  required
                />
              </label>
              <label className="campo">
                <span>Tipo de proceso *</span>
                <select
                  value={formulario.tipo_proceso}
                  onChange={(e) => setFormulario({ ...formulario, tipo_proceso: e.target.value })}
                >
                  {opciones(TIPOS_PROCESO).map(({ valor, etiqueta: nombre }) => (
                    <option key={valor} value={valor}>
                      {nombre}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="campo">
              <span>Asunto *</span>
              <input
                value={formulario.asunto}
                onChange={(e) => setFormulario({ ...formulario, asunto: e.target.value })}
                required
              />
            </label>

            <div className="rejilla-form">
              <label className="campo">
                <span>Cliente *</span>
                <input
                  value={formulario.cliente}
                  onChange={(e) => setFormulario({ ...formulario, cliente: e.target.value })}
                  required
                />
              </label>
              <label className="campo">
                <span>Estado</span>
                <select
                  value={formulario.estado}
                  onChange={(e) => setFormulario({ ...formulario, estado: e.target.value })}
                >
                  {opciones(ESTADOS_EXPEDIENTE).map(({ valor, etiqueta: nombre }) => (
                    <option key={valor} value={valor}>
                      {nombre}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="campo">
              <span>Abogado responsable</span>
              <select
                value={formulario.abogado_responsable_id}
                onChange={(e) =>
                  setFormulario({ ...formulario, abogado_responsable_id: e.target.value })
                }
              >
                <option value="">— Sin asignar (se asignará a usted) —</option>
                {abogados.map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.nombre_completo}
                  </option>
                ))}
              </select>
            </label>

            <label className="campo">
              <span>Descripción</span>
              <textarea
                rows={3}
                value={formulario.descripcion}
                onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
              />
            </label>

            <fieldset className="campo">
              <legend>Usuarios con acceso autorizado</legend>
              <div className="lista-checks">
                {personas.map((persona) => (
                  <label key={persona.id} className="check">
                    <input
                      type="checkbox"
                      checked={formulario.usuarios_autorizados.includes(persona.id)}
                      onChange={() => alternarAutorizado(persona.id)}
                    />
                    <span>
                      {persona.nombre_completo}
                      <small> ({persona.rol})</small>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="formulario-acciones">
              <button type="button" className="boton" onClick={() => setFormulario(null)}>
                Cancelar
              </button>
              <button type="submit" className="boton boton-primario">
                {editandoId ? 'Guardar cambios' : 'Crear expediente'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
