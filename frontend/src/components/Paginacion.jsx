import { useMemo } from 'react'

export default function Paginacion({ pagina, porPagina, total, paginas, onPaginaCambio }) {
  const info = useMemo(() => {
    if (total <= 0) return ''
    const inicio = (pagina - 1) * porPagina + 1
    const fin = Math.min(pagina * porPagina, total)
    return `${inicio}–${fin} de ${total}`
  }, [pagina, porPagina, total])

  if (total <= porPagina && pagina <= 1) {
    return null
  }

  const tieneAnterior = pagina > 1
  const tieneSiguiente = paginas > 0 ? pagina < paginas : (pagina * porPagina < total)

  return (
    <div className="paginacion" role="navigation" aria-label="Paginación">
      <span className="paginacion-info">{info}</span>
      <div className="paginacion-acciones">
        <button
          type="button"
          className="boton boton-mini"
          disabled={!tieneAnterior}
          onClick={() => onPaginaCambio(pagina - 1)}
        >
          Anterior
        </button>
        <span className="paginacion-pagina">
          Página {pagina}
          {paginas > 0 ? ` de ${paginas}` : ''}
        </span>
        <button
          type="button"
          className="boton boton-mini"
          disabled={!tieneSiguiente}
          onClick={() => onPaginaCambio(pagina + 1)}
        >
          Siguiente
        </button>
      </div>
    </div>
  )
}
