// Pruebas del bus de notificaciones (pub/sub de toasts).
import { afterEach, describe, expect, it, vi } from 'vitest'

import { alNotificar, notificar } from '../src/utils/notificar.js'

describe('notificar (bus de avisos)', () => {
  const cancelaciones = []

  function suscribir(fn) {
    const cancelar = alNotificar(fn)
    cancelaciones.push(cancelar)
    return cancelar
  }

  afterEach(() => {
    while (cancelaciones.length) cancelaciones.pop()()
  })

  it('emitía a todos los suscriptores activos', () => {
    const primero = vi.fn()
    const segundo = vi.fn()
    suscribir(primero)
    suscribir(segundo)

    notificar({ tipo: 'error', mensaje: 'Fallo', origen: 'prueba' })

    expect(primero).toHaveBeenCalledTimes(1)
    expect(segundo).toHaveBeenCalledTimes(1)
    expect(primero).toHaveBeenCalledWith({ tipo: 'error', mensaje: 'Fallo', origen: 'prueba' })
  })

  it('normaliza el tipo por defecto y admite mensajes en crudo', () => {
    const fn = vi.fn()
    suscribir(fn)

    notificar('Solo un texto')

    expect(fn).toHaveBeenCalledWith({ tipo: 'info', mensaje: 'Solo un texto', origen: undefined })
  })

  it('ignora notificaciones vacías sin error', () => {
    const fn = vi.fn()
    suscribir(fn)

    expect(() => notificar(undefined)).not.toThrow()
    expect(() => notificar({ mensaje: '' })).not.toThrow()
    expect(fn).not.toHaveBeenCalled()
  })

  it('un suscriptor que lanza excepción no interrumpe a los demás', () => {
    const roto = vi.fn(() => {
      throw new Error('suscriptor defectuoso')
    })
    const sano = vi.fn()
    suscribir(roto)
    suscribir(sano)

    expect(() => notificar({ tipo: 'error', mensaje: 'Fallo' })).not.toThrow()
    expect(sano).toHaveBeenCalledTimes(1)
  })

  it('al cancelar la suscripción deja de recibir avisos', () => {
    const fn = vi.fn()
    const cancelar = suscribir(fn)

    notificar({ mensaje: 'primero' })
    cancelar()
    notificar({ mensaje: 'segundo' })

    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('funciona sin suscriptores (no-op)', () => {
    expect(() => notificar({ tipo: 'error', mensaje: 'huérfana' })).not.toThrow()
  })
})
