// Pruebas de la capa global de toasts (ToastProvider + componente Toast).
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider, useToast } from '../src/context/ToastContext.jsx'
import { notificar } from '../src/utils/notificar.js'

/** Componente de práctica para disparar toasts desde el hook. */
function Practica() {
  const { error, exito, mostrar } = useToast()
  return (
    <div>
      <button type="button" onClick={() => error('No se pudo guardar el expediente.')}>
        provocar-error
      </button>
      <button type="button" onClick={() => exito('Cambios guardados.')}>
        provocar-exito
      </button>
      <button type="button" onClick={() => mostrar('info', 'Aviso informativo.')}>
        provocar-info
      </button>
    </div>
  )
}

function pintar() {
  return render(
    <ToastProvider>
      <Practica />
    </ToastProvider>,
  )
}

function rechazoNoCapturado(mensaje) {
  const evento = new Event('unhandledrejection')
  Object.defineProperty(evento, 'reason', { value: new Error(mensaje) })
  window.dispatchEvent(evento)
}

describe('ToastProvider', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renderiza un toast de error con role alert desde el hook', () => {
    pintar()

    fireEvent.click(screen.getByRole('button', { name: 'provocar-error' }))

    const alerta = screen.getByRole('alert')
    expect(alerta).toHaveTextContent('No se pudo guardar el expediente.')
    expect(alerta.className).toContain('toast-error')
    expect(screen.getByText('Error')).toBeTruthy()
  })

  it('renderiza toasts emitidos por el bus (como hace el cliente HTTP)', async () => {
    pintar()

    act(() => {
      notificar({ tipo: 'error', mensaje: 'No se pudo conectar con el servidor.', origen: 'conexion' })
    })

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo conectar con el servidor.',
    )
  })

  it('cierra el toast con el botón de cerrar', () => {
    pintar()
    fireEvent.click(screen.getByRole('button', { name: 'provocar-error' }))

    fireEvent.click(screen.getByRole('button', { name: 'Cerrar notificación' }))

    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('se cierra automáticamente tras la duración del error (7 s)', () => {
    vi.useFakeTimers()
    pintar()
    fireEvent.click(screen.getByRole('button', { name: 'provocar-error' }))
    expect(screen.getByRole('alert')).toBeTruthy()

    act(() => {
      vi.advanceTimersByTime(6999)
    })
    expect(screen.getByRole('alert')).toBeTruthy()

    act(() => {
      vi.advanceTimersByTime(2)
    })
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('los mensajes repetidos se deduplican (ráfagas de peticiones paralelas)', () => {
    pintar()

    act(() => {
      notificar({ tipo: 'error', mensaje: 'Sin conexión.', origen: 'conexion' })
      notificar({ tipo: 'error', mensaje: 'Sin conexión.', origen: 'conexion' })
      notificar({ tipo: 'error', mensaje: 'Sin conexión.', origen: 'conexion' })
    })

    expect(screen.getAllByRole('alert')).toHaveLength(1)
  })

  it('mantiene como máximo 4 toasts visibles', () => {
    pintar()

    act(() => {
      for (let i = 1; i <= 6; i += 1) {
        notificar({ tipo: 'error', mensaje: `Fallo número ${i}.` })
      }
    })

    const avisos = screen.getAllByRole('alert')
    expect(avisos).toHaveLength(4)
    // Los más antiguos se descartan: se conservan los últimos.
    expect(avisos[0]).toHaveTextContent('Fallo número 3.')
    expect(avisos[3]).toHaveTextContent('Fallo número 6.')
  })

  it('convierte un error de tipos (exito/info) en role status', () => {
    pintar()

    fireEvent.click(screen.getByRole('button', { name: 'provocar-exito' }))
    fireEvent.click(screen.getByRole('button', { name: 'provocar-info' }))

    expect(screen.getAllByRole('status')).toHaveLength(2)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('una promesa rechazada sin capturar ya no desaparece en silencio', () => {
    pintar()

    act(() => {
      rechazoNoCapturado('Algo falló sin capturar')
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Algo falló sin capturar')
  })

  it('useToast fuera del proveedor lanza un error claro', () => {
    // React imprime el error en consola al no haber boundary: se silencia aquí.
    const errorConsola = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      function Huérfana() {
        useToast()
        return null
      }
      expect(() => render(<Huérfana />)).toThrow('useToast debe usarse dentro de ToastProvider')
    } finally {
      errorConsola.mockRestore()
    }
  })
})
