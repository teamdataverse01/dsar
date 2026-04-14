import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'

import IntakeForm from './pages/IntakeForm'
import VerificationPage from './pages/VerificationPage'
import RequestStatus from './pages/RequestStatus'
import AdminLogin from './pages/admin/AdminLogin'
import AdminQueue from './pages/admin/AdminQueue'
import AdminRequestDetail from './pages/admin/AdminRequestDetail'
import ProtectedRoute from './components/ProtectedRoute'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Subject-facing */}
        <Route path="/" element={<Navigate to="/request/new" replace />} />
        <Route path="/request/new" element={<IntakeForm />} />
        <Route path="/request/verify/:requestId" element={<VerificationPage />} />
        <Route path="/request/status/:reference" element={<RequestStatus />} />

        {/* Admin */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/queue" element={<ProtectedRoute><AdminQueue /></ProtectedRoute>} />
        <Route path="/admin/requests/:id" element={<ProtectedRoute><AdminRequestDetail /></ProtectedRoute>} />

        <Route path="*" element={<Navigate to="/request/new" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
