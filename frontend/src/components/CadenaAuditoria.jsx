/** Cadena de auditoría animada (Módulo 6, mejora #7).
 *
 * Grafo vertical de eslabones: cada registro muestra su `hash_anterior` y su
 * `hash_actual` truncados por ambos extremos, y el conector visualiza el
 * enlace real entre eslabones. Al verificar, un barrido recorre la cadena de
 * arriba abajo y el resultado se aplica eslabón a eslabón: los válidos en
 * verde, el **primer eslabón roto** en rojo (con latido) y todo lo posterior
 * queda marcado como «no confiable», porque la cadena se rompe hacia abajo.
 *
 * El componente es solo presentacional: el cálculo de la integridad lo hace
 * el servidor (`GET /auditoria/verificar`) y los datos llegan de
 * `GET /auditoria` ya encadenados. La animación se omite con
 * `prefers-reduced-motion`.
 */

import { Fragment, useEffect, useState } from 'react'

import Insignia from './Insignia.jsx'
import { ACCIONES_AUDITORIA } from '../constants.js'
import { etiqueta, fechaHora, hashCorto } from '../utils/format.js'

/** Primer eslabón de la cadena: valor fijo conocido por todos. */
export const HASH_GENESIS = '0'.repeat(64)

/** Eslabones visibles por defecto antes de plegar la cadena. */
export const VENTANA_DEFECTO = 15

// Duración del barrido: ~1,6 s en total, repartidos entre los eslabones.
const PASO_MIN_MS = 35
const PASO_MAX_MS = 90

const ESTADOS = {
  pendiente: { etiqueta: 'Sin verificar', tono: 'neutro' },
  barriendo: { etiqueta: 'Verificando…', tono: 'azul' },
  ok: { etiqueta: 'Válido', tono: 'verde' },
  roto: { etiqueta: 'Roto', tono: 'rojo' },
  alterado: { etiqueta: 'No confiable', tono: 'ambar' },
}

/** ¿Pide el usuario/entorno reducir las animaciones? */
export function movimientoReducido() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Estado visual de un eslabón (índice global, 0-based) según el resultado de
 * la verificación y el avance del barrido.
 */
export function estadoEslabon(indice, verificacion, avance) {
  if (!verificacion) return avance > indice ? 'barriendo' : 'pendiente'
  if (verificacion.integro) return 'ok'
  const roto = verificacion.indice_roto
  // Un registro inválido sin posición concreta invalida la cadena entera.
  if (roto == null) return 'alterado'
  if (indice < roto) return 'ok'
  if (indice === roto) return 'roto'
  return 'alterado'
}

export default function CadenaAuditoria({
  registros = [],
  verificacion = null,
  verificando = false,
  onVerificar,
}) {
  const [avance, setAvance] = useState(0)
  const [resultado, setResultado] = useState(null)
  const [expandida, setExpandida] = useState(false)

  const total = registros.length
  const ventana = expandida ? total : Math.min(VENTANA_DEFECTO, total)
  const inicio = total - ventana
  const visibles = registros.slice(inicio)

  // Barrido animado: recorre los eslabones visibles y, al terminar, aplica el
  // resultado real de la verificación del servidor.
  useEffect(() => {
    if (!verificacion) {
      setResultado(null)
      setAvance(0)
      return undefined
    }
    if (movimientoReducido() || ventana === 0) {
      setResultado(verificacion)
      setAvance(ventana)
      return undefined
    }
    setResultado(null)
    setAvance(0)
    const paso = Math.min(
      PASO_MAX_MS,
      Math.max(PASO_MIN_MS, Math.floor(1600 / Math.max(ventana, 1))),
    )
    let contador = 0
    const temporizador = setInterval(() => {
      contador += 1
      setAvance(contador)
      if (contador >= ventana) {
        clearInterval(temporizador)
        setResultado(verificacion)
      }
    }, paso)
    return () => clearInterval(temporizador)
    // `verificacion` es un objeto nuevo en cada verificación: el efecto se
    // relanza siempre con el resultado más reciente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verificacion, ventana])

  // Estado global para la insignia de cabecera y la línea de resultado:
  // «barriendo» mientras el servidor responde y mientras corre la animación.
  let estadoGlobal = 'pendiente'
  if (verificando || (verificacion && !resultado)) estadoGlobal = 'barriendo'
  else if (resultado?.integro) estadoGlobal = 'ok'
  else if (resultado) estadoGlobal = 'roto'

  return (
    <section className="panel cadena-panel" aria-label="Cadena de integridad de la auditoría">
      <div className="panel-cabecera">
        <div className="cadena-titulo">
          <h2>Cadena de integridad</h2>
          <Insignia tono={ESTADOS[estadoGlobal].tono}>{ESTADOS[estadoGlobal].etiqueta}</Insignia>
        </div>
        {onVerificar && (
          <button
            type="button"
            className="boton boton-mini"
            onClick={onVerificar}
            disabled={verificando}
          >
            {verificando ? 'Verificando…' : 'Verificar cadena'}
          </button>
        )}
      </div>

      <p className="nota">
        Cada registro guarda el hash SHA-256 del anterior: alterar, insertar o reordenar un
        eslabón rompe la cadena desde ese punto hacia abajo.
      </p>

      {total === 0 ? (
        <p className="vacio">Todavía no hay registros en la auditoría.</p>
      ) : (
        <>
          <ol className="cadena" aria-label="Eslabones de la cadena de auditoría">
            <li className="eslabon eslabon-genesis" data-testid="eslabon-genesis">
              <div className="eslabon-cabecera">
                <span className="eslabon-numero">Génesis</span>
                <span className="eslabon-meta">Primer eslabón (valor conocido por todos)</span>
              </div>
              <div className="eslabon-hash" title={HASH_GENESIS}>
                <span className="hash-etiqueta">raíz</span> {hashCorto(HASH_GENESIS, 8, 6)}
              </div>
            </li>

            {visibles.map((registro, posicion) => {
              const indice = inicio + posicion
              const estado = estadoEslabon(indice, resultado, avance)
              const previo = posicion === 0 ? { hash_actual: HASH_GENESIS } : visibles[posicion - 1]
              return (
                <Fragment key={registro.id}>
                  <li className={`eslabon-conector conector-${estado}`}>
                    <span className="conector-hash" title={previo.hash_actual}>
                      {hashCorto(previo.hash_actual, 8, 6)}
                    </span>
                    <span className="conector-flecha" aria-hidden="true">
                      ↓
                    </span>
                    {estado === 'ok' && (
                      <span className="conector-ok" title="Enlace verificado">
                        ✓ enlace verificado
                      </span>
                    )}
                    {estado === 'roto' && (
                      <span className="conector-roto">✕ el enlace no coincide</span>
                    )}
                    {estado === 'alterado' && (
                      <span className="conector-alterado">… posterior a la rotura</span>
                    )}
                  </li>
                  <li
                    className={`eslabon eslabon-${estado}`}
                    data-testid="eslabon"
                    data-indice={indice}
                    style={{ '--i': Math.min(posicion, 10) }}
                  >
                    <div className="eslabon-cabecera">
                      <span className="eslabon-numero">#{indice + 1}</span>
                      <Insignia tono={ESTADOS[estado].tono}>{ESTADOS[estado].etiqueta}</Insignia>
                      <span className="eslabon-meta">
                        {fechaHora(registro.creado_en)} · {registro.usuario || 'sistema'} ·{' '}
                        {etiqueta(ACCIONES_AUDITORIA, registro.accion)}
                      </span>
                    </div>
                    <div className="eslabon-hash" title={registro.hash_anterior}>
                      <span className="hash-etiqueta">anterior</span>{' '}
                      {hashCorto(registro.hash_anterior, 8, 6)}
                    </div>
                    <div className="eslabon-hash" title={registro.hash_actual}>
                      <span className="hash-etiqueta">eslabón</span>{' '}
                      {hashCorto(registro.hash_actual, 8, 6)}
                    </div>
                  </li>
                </Fragment>
              )
            })}
          </ol>

          <div className="cadena-pie">
            <p className="cadena-estado" role="status" aria-live="polite">
              {(verificando || (verificacion && !resultado)) &&
                'Recorriendo la cadena eslabón a eslabón…'}
              {!verificando && resultado?.integro && (
                <>
                  <strong className="cadena-ok">Cadena íntegra:</strong> {resultado.total}{' '}
                  eslabones verificados el {fechaHora(resultado.verificado_en)}.
                </>
              )}
              {!verificando && resultado && !resultado.integro && (
                <>
                  <strong className="cadena-roto">¡Cadena rota!</strong> El primer eslabón inválido
                  es el #{(resultado.indice_roto ?? 0) + 1}; nada de lo que sigue es confiable.
                </>
              )}
              {!verificando && !verificacion && 'Pulsa «Verificar cadena» para recalcularla.'}
            </p>

            <div className="cadena-leyenda" aria-hidden="true">
              <span className="leyenda-item leyenda-ok">● válido</span>
              <span className="leyenda-item leyenda-roto">● roto</span>
              <span className="leyenda-item leyenda-alterado">● no confiable</span>
            </div>
          </div>

          {total > VENTANA_DEFECTO && (
            <button
              type="button"
              className="boton boton-mini cadena-expandir"
              onClick={() => setExpandida((valor) => !valor)}
            >
              {expandida
                ? `Mostrar solo los últimos ${VENTANA_DEFECTO} eslabones`
                : `Ver toda la cadena (${total} eslabones)`}
            </button>
          )}
        </>
      )}
    </section>
  )
}
