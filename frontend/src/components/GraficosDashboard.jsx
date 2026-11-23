import { useMemo } from 'react'

/**
 * Gráfico interactivo y minimalista de distribución (Donut / Barra de proporción).
 * No requiere librerías pesadas externas, súper rápido, accesible y animado con SVG.
 */
export function GraficoDonut({ datos = [], titulo, totalEtiqueta = 'Total' }) {
  const total = useMemo(() => datos.reduce((sum, d) => sum + (d.valor || 0), 0), [datos])

  // Cálculo de segmentos para el donut SVG
  const radio = 38
  const circunferencia = 2 * Math.PI * radio

  let desplazamientoAcumulado = 0
  const segmentos = datos.map((item) => {
    const porcentaje = total > 0 ? item.valor / total : 0
    const longitud = porcentaje * circunferencia
    const segmento = {
      ...item,
      porcentaje: Math.round(porcentaje * 100),
      dasharray: `${longitud} ${circunferencia - longitud}`,
      dashoffset: -desplazamientoAcumulado,
    }
    desplazamientoAcumulado += longitud
    return segmento
  })

  return (
    <div className="grafico-card">
      <div className="grafico-cabecera">
        <h4>{titulo}</h4>
        <span className="grafico-badge">{total} en total</span>
      </div>

      <div className="grafico-donut-cuerpo">
        <div className="donut-svg-wrapper">
          <svg viewBox="0 0 100 100" className="donut-svg" width="110" height="110">
            {/* Círculo base de fondo */}
            <circle
              cx="50"
              cy="50"
              r={radio}
              fill="transparent"
              stroke="#f1f5f9"
              strokeWidth="11"
            />
            {total > 0 &&
              segmentos.map((seg, idx) => (
                <circle
                  key={seg.etiqueta || idx}
                  cx="50"
                  cy="50"
                  r={radio}
                  fill="transparent"
                  stroke={seg.color || '#3b82f6'}
                  strokeWidth="11"
                  strokeDasharray={seg.dasharray}
                  strokeDashoffset={seg.dashoffset}
                  className="donut-segmento"
                  strokeLinecap="round"
                />
              ))}
          </svg>
          <div className="donut-centro">
            <span className="donut-centro-valor">{total}</span>
            <span className="donut-centro-etiqueta">{totalEtiqueta}</span>
          </div>
        </div>

        <div className="grafico-leyenda">
          {datos.length === 0 || total === 0 ? (
            <p className="vacio-mini">Sin registros suficientes</p>
          ) : (
            segmentos.map((item) => (
              <div key={item.etiqueta} className="leyenda-item">
                <span className="leyenda-punto" style={{ background: item.color }} />
                <span className="leyenda-nombre">{item.etiqueta}</span>
                <span className="leyenda-conteo">{item.valor}</span>
                <span className="leyenda-pct">({item.porcentaje}%)</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Gráfico de barras horizontales compacto para actividad o distribución por categoría.
 */
export function GraficoBarras({ datos = [], titulo }) {
  const maximo = useMemo(() => Math.max(...datos.map((d) => d.valor || 0), 1), [datos])

  return (
    <div className="grafico-card">
      <div className="grafico-cabecera">
        <h4>{titulo}</h4>
      </div>

      <div className="grafico-barras-lista">
        {datos.length === 0 ? (
          <p className="vacio-mini">Sin registros</p>
        ) : (
          datos.map((item) => {
            const porcentaje = Math.round(((item.valor || 0) / maximo) * 100)
            return (
              <div key={item.etiqueta} className="barra-fila">
                <div className="barra-info">
                  <span className="barra-etiqueta">{item.etiqueta}</span>
                  <strong className="barra-valor">{item.valor}</strong>
                </div>
                <div className="barra-pista">
                  <div
                    className="barra-progreso"
                    style={{
                      width: `${porcentaje}%`,
                      background: item.color || '#1d4ed8',
                    }}
                  />
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
