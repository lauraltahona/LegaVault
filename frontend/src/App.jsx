import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout.jsx'
import RutaProtegida from './components/RutaProtegida.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import AlertasPage from './pages/AlertasPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import DocumentosPage from './pages/DocumentosPage.jsx'
import ExpedienteDetallePage from './pages/ExpedienteDetallePage.jsx'
import ExpedientesPage from './pages/ExpedientesPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import UsuariosPage from './pages/UsuariosPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <RutaProtegida>
                <Layout />
              </RutaProtegida>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/expedientes" element={<ExpedientesPage />} />
            <Route path="/expedientes/:id" element={<ExpedienteDetallePage />} />
            <Route path="/documentos" element={<DocumentosPage />} />
            <Route
              path="/usuarios"
              element={
                <RutaProtegida roles={['admin']}>
                  <UsuariosPage />
                </RutaProtegida>
              }
            />
            <Route
              path="/alertas"
              element={
                <RutaProtegida roles={['admin']}>
                  <AlertasPage />
                </RutaProtegida>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
