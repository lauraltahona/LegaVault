// Pruebas de la paginación (Módulo 4, mejora #10): helper `itemsDe` y
// comportamiento de paginado en AlertasPage.
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AlertasPage from '../src/pages/AlertasPage.jsx'
import { listarAlertas, marcarAlertaLeida, marcarTodasLeidas, resumenAlertas } from '../src/api/alertas.js'
import { itemsDe } from '../src/utils/paginacion.js'

vi.mock('../src/api/alertas.js', () => ({
  listarAlertas: vi.fn(),
  marcarAlertaLeida: vi.fn(),
  marcarTodasLeidas: vi.fn(),
  resumenAlertas: vi.fn(),
}))

describe('itemsDe (tolerancia array | objeto paginado)', () => {
  it('devuelve el mismo array si la respuesta ya es una lista', () => {
    const lista = [{ id: 1 }, { id: 2 }]
    expect(itemsDe(lista)).toBe(lista)
  })

  it('extrae `items` de una respuesta paginada', () => {
    const items = [{ id: 3 }]
    expect(itemsDe({ items, total: 41, pagina: 2, por_pagina: 20, paginas: 3 })).toBe(items)
  })

  it('devuelve [] ante respuestas nulas, undefined o malformadas', () => {
    expect(itemsDe(null)).toEqual([])
    expect(itemsDe(undefined)).toEqual([])
    expect(itemsDe({})).toEqual([])
    expect(itemsDe({ total: 5 })).toEqual([])
  })
})

describe('AlertasPage paginado', () => {
  beforeEach(() => {
    listarAlertas.mockReset()
    resumenAlertas.mockReset()
    marcarAlertaLeida.mockReset()
    marcarTodasLeidas.mockReset()
    resumenAlertas.mockResolvedValue({ total: 45, no_leidas: 7, por_severidad: {} })
    marcarAlertaLeida.mockResolvedValue({})
    marcarTodasLeidas.mockResolvedValue({})
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  function alertaDe(indice) {
    return {
      id: `a-${indice}`,
      tipo: 'login_fallido',
      severidad: 'advertencia',
      usuario: `usuario${indice}`,
      mensaje: `Alerta ${indice}`,
      leida: false,
      creado_en: '2026-10-19T10:00:00Z',
    }
  }

  it('pide la primera página al montar y muestra el rango de la respuesta', async () => {
    listarAlertas.mockResolvedValue({
      items: [alertaDe(1), alertaDe(2)],
      total: 45,
      pagina: 1,
      por_pagina: 20,
      paginas: 3,
    })

    render(<AlertasPage />)

    await waitFor(() => {
      expect(listarAlertas).toHaveBeenCalledWith({
        tipo: '',
        severidad: '',
        usuario: '',
        solo_no_leidas: false,
        pagina: 1,
        por_pagina: 20,
      })
    })
    expect(await screen.findByText('Alerta 1')).toBeTruthy()
    expect(screen.getByText(/1–20 de 45/)).toBeTruthy()
    expect(screen.getByText('Página 1 de 3')).toBeTruthy()
  })

  it('al pulsar «Siguiente» refetch con la página siguiente', async () => {
    listarAlertas.mockResolvedValue({
      items: [alertaDe(21)],
      total: 45,
      pagina: 1,
      por_pagina: 20,
      paginas: 3,
    })

    render(<AlertasPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Siguiente' }))

    await waitFor(() => {
      expect(listarAlertas).toHaveBeenCalledWith(
        expect.objectContaining({ pagina: 2 }),
      )
    })
  })

  it('si el backend responde una lista simple, funciona sin paginación', async () => {
    listarAlertas.mockResolvedValue([alertaDe(1)])

    render(<AlertasPage />)

    expect(await screen.findByText('Alerta 1')).toBeTruthy()
    // Con ≤20 items y página 1, el control de paginación no se renderiza.
    expect(screen.queryByRole('navigation', { name: 'Paginación' })).toBeNull()
  })
})
