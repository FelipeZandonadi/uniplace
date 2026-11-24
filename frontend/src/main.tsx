import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, ProtectedRoute } from './auth';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { AuthCallback } from './pages/AuthCallback';
import { Mural } from './pages/Mural';
import { NovoAviso } from './pages/NovoAviso';
import { Vagas } from './pages/Vagas';
import { NovaVaga } from './pages/NovaVaga';
import { CandidaturasVaga } from './pages/CandidaturasVaga';
import { MinhasCandidaturas } from './pages/MinhasCandidaturas';
import { NotFound } from './pages/NotFound';
import './styles.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route index element={<Mural />} />
              <Route path="/mural/novo" element={<NovoAviso />} />
              <Route path="/vagas" element={<Vagas />} />
              <Route path="/vagas/nova" element={<NovaVaga />} />
              <Route path="/vagas/:id/candidaturas" element={<CandidaturasVaga />} />
              <Route path="/minhas-candidaturas" element={<MinhasCandidaturas />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/sw.js');
  });
}
