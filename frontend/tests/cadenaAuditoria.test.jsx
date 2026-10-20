// Pruebas de la cadena de auditoría animada (Módulo 6, mejora #7).
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CadenaAuditoria, {
  HASH_GENESIS,
  VENTANA_DEFECTO,
  estadoEslabon,
} from '../src/components/CadenaAuditoria.jsx'
import AuditoriaPage from '../src/pages/AuditoriaPage.jsx'
import { listarAuditoria, resumenAuditoria, verificarAuditoria } from '../src/api/auditoria.js'

// El módulo de API se sustituye por dobles: las pruebas no tocan la red.
vi.mock('../src/api/auditoria.js', () => ({
  listarAuditoria: vi.fn(),
  resumenAuditoria: vi.fn(),
  verificarAuditoria: vi.fn(),
}))

/** Hash de 64 caracteres determinista e inequívoco por eslabón (letra + relleno). */
const LETRAS = 'abcdefghij'

function hashDe(indice) {
  if (indice < 0) return HASH_GENESIS
  return LETRAS[indice % LETRAS.length].repeat(64)
}

/** Registro de cadena con hashes encadenados y deterministas. */
function crearRegistro(indice) {
  const numero = String(indice).padStart(2, '0')
  return {
    id: `reg-${indice}`,
    accion: 'login',
    resultado: 'ok',
    entidad: '',
    entidad_id: '',
    usuario: `usuario${indice}`,
    usuario_id: `u-${indice}`,
    rol: 'admin',
    detalle: `Detalle ${indice}`,
    ip: '127.0.0.1',
    creado_en: `2026-10-19T10:00:${numero}Z`,
    hash_anterior: hashDe(indice - 1),
    hash_actual: hashDe(indice),
  }
}

function crearCadena(desde, hasta) {
  const registros = []
  for (let i = desde; i <= hasta; i += 1) registros.push(crearRegistro(i))
  return registros
}

function eslabonDe(indice) {
  return document.querySelector(`[data-indice="${indice}"]`)
}

describe('estadoEslabon (lógica pura)', () => {
  it('marca todos como pendientes antes de verificar', () => {
    expect(estadoEslabon(0, null, 0)).toBe('pendiente')
    expect(estadoEslabon(5, null, 0)).toBe('pendiente')
  })

  it('durante el barrido los eslabones recorridos están «barriendo»', () => {
    expect(estadoEslabon(0, null, 2)).toBe('barriendo')
    expect(estadoEslabon(1, null, 2)).toBe('barriendo')
    expect(estadoEslabon(2, null, 2)).toBe('pendiente')
  })

  it('con cadena íntegra todos los eslabones son válidos', () => {
    const verificacion = { integro: true, total: 3, indice_roto: null }
    expect([0, 1, 2].map((i) => estadoEslabon(i, verificacion, 3))).toEqual(['ok', 'ok', 'ok'])
  })

  it('con la cadena rota solo el eslabón señalado es «roto»', () => {
    const verificacion = { integro: false, total: 4, indice_roto: 2 }
    expect([0, 1, 2, 3].map((i) => estadoEslabon(i, verificacion, 4))).toEqual([
      'ok',
      'ok',
      'roto',
      'alterado',
    ])
  })

  it('un índice roto nulo invalida la cadena entera (defensa)', () => {
    const verificacion = { integro: false, total: 2, indice_roto: null }
    expect(estadoEslabon(0, verificacion, 2)).toBe('alterado')
    expect(estadoEslabon(1, verificacion, 2)).toBe('alterado')
  })
})

describe('componente CadenaAuditoria', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra el génesis y los eslabones con hashes truncados por ambos extremos', () => {
    render(<CadenaAuditoria registros={crearCadena(0, 2)} />)

    expect(screen.getByTestId('eslabon-genesis')).toBeTruthy()
    const eslabones = screen.getAllByTestId('eslabon')
    expect(eslabones).toHaveLength(3)
    // El eslabón #1 enlaza con el génesis (64 ceros) y muestra su propio hash…
    expect(eslabones[0].textContent).toContain('00000000…000000')
    expect(eslabones[0].textContent).toContain('aaaaaaaa…aaaaaa')
    // …y el #3 muestra el hash del #2 y el suyo, truncados por ambos extremos.
    expect(eslabones[2].textContent).toContain('bbbbbbbb…bbbbbb')
    expect(eslabones[2].textContent).toContain('cccccccc…cccccc')
    // El hash completo queda disponible al pasar el cursor.
    expect(eslabones[2].querySelector(`[title="${'c'.repeat(64)}"]`)).toBeTruthy()
    expect(eslabones[2].getAttribute('data-indice')).toBe('2')
  })

  it('muestra el estado vacío cuando no hay registros', () => {
    render(<CadenaAuditoria registros={[]} />)
    expect(screen.getByText('Todavía no hay registros en la auditoría.')).toBeTruthy()
  })

  it('numera los eslabones en orden cronológico con sus metadatos', () => {
    render(<CadenaAuditoria registros={crearCadena(0, 2)} />)

    const eslabones = screen.getAllByTestId('eslabon')
    expect(eslabones[0].getAttribute('data-indice')).toBe('0')
    expect(eslabones[0].textContent).toContain('#1')
    expect(eslabones[0].textContent).toContain('usuario0')
    expect(eslabones[2].textContent).toContain('#3')
  })

  it('al verificar una cadena íntegra la barre y marca todos los enlaces válidos', async () => {
    render(
      <CadenaAuditoria
        registros={crearCadena(0, 2)}
        verificacion={{ integro: true, total: 3, indice_roto: null, verificado_en: '2026-10-19T12:00:00Z' }}
      />,
    )

    await waitFor(() => {
      expect(document.querySelectorAll('.eslabon-ok')).toHaveLength(3)
    })
    expect(document.querySelectorAll('.eslabon-roto')).toHaveLength(0)
    // Los conectores confirman el enlace verificado entre génesis y eslabones.
    expect(screen.getAllByText('✓ enlace verificado')).toHaveLength(3)
    expect(screen.getByText(/Cadena íntegra/)).toBeTruthy()
    expect(screen.getByText(/3 eslabones verificados/)).toBeTruthy()
  })

  it('resalta el primer eslabón roto y marca el resto como no confiable', async () => {
    render(
      <CadenaAuditoria
        registros={crearCadena(0, 3)}
        verificacion={{ integro: false, total: 4, indice_roto: 1, verificado_en: '2026-10-19T12:00:00Z' }}
      />,
    )

    await waitFor(() => {
      expect(eslabonDe(1)?.className).toContain('eslabon-roto')
    })
    // Anterior a la rotura: válido. Rotura: resaltado. Posterior: no confiable.
    expect(eslabonDe(0).className).toContain('eslabon-ok')
    expect(eslabonDe(2).className).toContain('eslabon-alterado')
    expect(eslabonDe(3).className).toContain('eslabon-alterado')
    // El conector del eslabón roto explica por qué no enlaza.
    expect(screen.getByText('✕ el enlace no coincide')).toBeTruthy()
    expect(screen.getAllByText('… posterior a la rotura')).toHaveLength(2)
    // La insignia y el pie de resumen señalan la rotura.
    expect(within(eslabonDe(1)).getByText('Roto')).toBeTruthy()
    expect(screen.getByText(/¡Cadena rota!/)).toBeTruthy()
    expect(screen.getByText(/es el #2/)).toBeTruthy()
  })

  it('con prefers-reduced-motion aplica el resultado sin barrido animado', async () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true })

    render(
      <CadenaAuditoria
        registros={crearCadena(0, 2)}
        verificacion={{ integro: true, total: 3, indice_roto: null, verificado_en: '2026-10-19T12:00:00Z' }}
      />,
    )

    // Sin pasos intermedios: el resultado aparece de inmediato.
    await waitFor(() => {
      expect(document.querySelectorAll('.eslabon-ok')).toHaveLength(3)
    })
    expect(document.querySelectorAll('.eslabon-barriendo')).toHaveLength(0)
    expect(window.matchMedia).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)')
  })

  it('pliega cadenas largas y permite desplegarlas por completo', () => {
    const cadena = crearCadena(1, VENTANA_DEFECTO + 5)
    render(<CadenaAuditoria registros={cadena} />)

    // Ventana por defecto: solo los últimos N eslabones (más el génesis).
    expect(screen.getAllByTestId('eslabon')).toHaveLength(VENTANA_DEFECTO)
    expect(eslabonDe(0)).toBeNull() // el más antiguo queda plegado
    expect(screen.getByText('Ver toda la cadena (20 eslabones)')).toBeTruthy()

    fireEvent.click(screen.getByText('Ver toda la cadena (20 eslabones)'))

    expect(screen.getAllByTestId('eslabon')).toHaveLength(20)
    expect(eslabonDe(0)).toBeTruthy()
    expect(screen.getByText('Mostrar solo los últimos 15 eslabones')).toBeTruthy()
  })

  it('ofrece verificar la cadena desde el propio panel', () => {
    const onVerificar = vi.fn()
    render(<CadenaAuditoria registros={crearCadena(0, 1)} onVerificar={onVerificar} />)

    fireEvent.click(screen.getByRole('button', { name: 'Verificar cadena' }))
    expect(onVerificar).toHaveBeenCalledTimes(1)
  })

  it('desactiva el botón de verificar mientras el servidor responde', () => {
    render(<CadenaAuditoria registros={crearCadena(0, 1)} verificando onVerificar={() => {}} />)

    const boton = screen.getByRole('button', { name: 'Verificando…' })
    expect(boton).toHaveProperty('disabled', true)
  })
})

describe('AuditoriaPage con la cadena integrada', () => {
  const cadenaDescendente = [crearRegistro(2), crearRegistro(1), crearRegistro(0)]
  const resumenDemo = {
    total: 3,
    por_resultado: { ok: 3, denegado: 0, error: 0 },
    por_accion: { login: 3 },
  }

  beforeEach(() => {
    listarAuditoria.mockReset()
    resumenAuditoria.mockReset()
    verificarAuditoria.mockReset()
    // El endpoint devuelve la cadena en orden descendente (más reciente
    // primero); la tabla pide filtros y la cadena llama sin argumentos.
    listarAuditoria.mockImplementation((params = {}) =>
      Object.keys(params).length === 0
        ? Promise.resolve(cadenaDescendente)
        : Promise.resolve(cadenaDescendente),
    )
    resumenAuditoria.mockResolvedValue(resumenDemo)
    verificarAuditoria.mockResolvedValue({
      integro: true,
      total: 3,
      indice_roto: null,
      verificado_en: '2026-10-19T12:00:00Z',
    })
  })

  it('carga la cadena completa y la reordena cronológicamente', async () => {
    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getAllByTestId('eslabon')).toHaveLength(3)
    })
    // Aunque el servidor devuelve lo más reciente primero, el eslabón #1 es el
    // más antiguo: así el indice_roto (0-based, orden del archivo) coincide.
    const eslabones = screen.getAllByTestId('eslabon')
    expect(eslabones[0].getAttribute('data-indice')).toBe('0')
    expect(eslabones[0].textContent).toContain('usuario0')
    expect(eslabones[2].textContent).toContain('usuario2')
    expect(listarAuditoria).toHaveBeenCalledWith({})
  })

  it('verifica la cadena desde la cabecera y la barre hasta el último eslabón', async () => {
    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getAllByTestId('eslabon')).toHaveLength(3)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar integridad' }))

    expect(await screen.findByText(/Cadena íntegra: 3 registros verificados/)).toBeTruthy()
    await waitFor(() => {
      expect(document.querySelectorAll('.eslabon-ok')).toHaveLength(3)
    })
    expect(verificarAuditoria).toHaveBeenCalledTimes(1)
  })

  it('señala el eslabón roto coherente en el aviso y en la cadena', async () => {
    verificarAuditoria.mockResolvedValue({
      integro: false,
      total: 3,
      indice_roto: 1,
      verificado_en: '2026-10-19T12:00:00Z',
    })
    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getAllByTestId('eslabon')).toHaveLength(3)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar integridad' }))

    // El aviso traduce el índice 0-based a un número de eslabón 1-based.
    expect(await screen.findByText(/La cadena está rota en el eslabón #2/)).toBeTruthy()
    await waitFor(() => {
      expect(eslabonDe(1)?.className).toContain('eslabon-roto')
    })
    expect(eslabonDe(0).className).toContain('eslabon-ok')
    expect(eslabonDe(2).className).toContain('eslabon-alterado')
  })

  it('muestra el error si la verificación falla sin dejar la cadena en un estado falso', async () => {
    verificarAuditoria.mockRejectedValue(new Error('Error 500'))
    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getAllByTestId('eslabon')).toHaveLength(3)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Verificar integridad' }))

    expect(await screen.findByText('Error 500')).toBeTruthy()
    // Ningún eslabón queda marcado como verificado.
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Verificar integridad' })).toBeTruthy()
    })
    expect(document.querySelectorAll('.eslabon-ok')).toHaveLength(0)
    expect(document.querySelectorAll('.eslabon-roto')).toHaveLength(0)
  })

  it('conserva la tabla de registros filtrada (regresión del módulo)', async () => {
    render(<AuditoriaPage />)

    expect(await screen.findByText('Detalle 2')).toBeTruthy()
    expect(screen.getByText('Detalle 0')).toBeTruthy()
    expect(screen.getByPlaceholderText('Usuario…')).toBeTruthy()
    // Los tres desplegables de filtro siguen presentes (acción, resultado, entidad).
    expect(screen.getAllByRole('combobox')).toHaveLength(3)
  })
})
