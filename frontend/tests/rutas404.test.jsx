// Pruebas de la página 404 y del enrutamiento (mejora #9).
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../src/App.jsx'
import { usuarioActual } from '../src/api/auth.js'

// El restore de sesión llama a /auth/me: se sustituye para aislar las pruebas.
vi.mock('../src/api/auth.js', () => ({
  usuarioActual: vi.fn(),
  iniciarSesion: vi.fn(),
  cerrarSesion: vi.fn(),
}))

const TOKEN = 'legalvault_token'

function irA(ruta) {
  window.history.pushState({}, '', ruta)
}

describe('página 404 y enrutamiento', () => {
  beforeEach(() => {
    localStorage.clear()
    irA('/')
    usuarioActual.mockReset()
  })

  describe('ruta desconocida sin sesión', () => {
    it('muestra la página 404 con la ruta solicitada en lugar de redirigir en silencio', async () => {
      irA('/ruta/que/no/existe')
      render(<App />)

      expect(await screen.findByText('Página no encontrada')).toBeTruthy()
      expect(screen.getByText('404')).toBeTruthy()
      expect(screen.getByText('/ruta/que/no/existe')).toBeTruthy()
      // No se ha redirigido al panel (el comportamiento anterior desapareció).
      expect(window.location.pathname).toBe('/ruta/que/no/existe')
    })

    it('ofrece volver a iniciar sesión', async () => {
      irA('/no-tiene-sentido')
      render(<App />)

      const enlace = await screen.findByRole('link', { name: 'Iniciar sesión' })
      expect(enlace.getAttribute('href')).toBe('/login')
    })
  })

  describe('ruta desconocida con sesión activa', () => {
    it('muestra la página 404 con salida al panel', async () => {
      localStorage.setItem(TOKEN, 'token-valido')
      usuarioActual.mockResolvedValue({
        username: 'admin',
        nombre_completo: 'Admin Demo',
        rol: 'admin',
      })
      irA('/expedientes/xxx/inexistente')
      render(<App />)

      const volver = await screen.findByRole('link', { name: 'Volver al panel' })
      expect(volver.getAttribute('href')).toBe('/')
      expect(screen.getByText('/expedientes/xxx/inexistente')).toBeTruthy()
      expect(screen.queryByText('Cargando…')).toBeNull()
    })
  })

  describe('regresión: las rutas conocidas siguen intactas', () => {
    it('/login renderiza el formulario de acceso', async () => {
      irA('/login')
      render(<App />)

      expect(await screen.findByText('LegalVault')).toBeTruthy()
      expect(screen.getByLabelText('Usuario')).toBeTruthy()
      expect(screen.getByLabelText('Contraseña')).toBeTruthy()
      expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeTruthy()
    })

    it('sin sesión, una ruta protegida sigue redirigiendo al login', async () => {
      irA('/expedientes')
      render(<App />)

      expect(await screen.findByRole('button', { name: 'Iniciar sesión' })).toBeTruthy()
      expect(window.location.pathname).toBe('/login')
    })

    it('la raíz sin sesión también termina en el login', async () => {
      irA('/')
      render(<App />)

      expect(await screen.findByRole('button', { name: 'Iniciar sesión' })).toBeTruthy()
    })
  })
})
