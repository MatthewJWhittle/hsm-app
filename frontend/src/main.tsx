import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import { AdminPage } from './admin/AdminPage.tsx'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthProvider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
