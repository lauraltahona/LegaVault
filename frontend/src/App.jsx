import { BrowserRouter, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout.jsx'
import RutaProtegida from './components/RutaProtegida.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import AlertasPage from './pages/AlertasPage.jsx'
import AuditoriaPage from './pages/AuditoriaPage.jsx'
import BovedaPage from './pages/BovedaPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import DocumentosPage from './pages/DocumentosPage.jsx'
import ExpedienteDetallePage from './pages/ExpedienteDetallePage.jsx'
import ExpedientesPage from './pages/ExpedientesPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import UsuariosPage from './pages/UsuariosPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
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
              <Route path="/boveda" element={<BovedaPage />} />
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
              <Route
                path="/auditoria"
                element={
                  <RutaProtegida roles={['admin']}>
                    <AuditoriaPage />
                  </RutaProtegida>
                }
              />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}
