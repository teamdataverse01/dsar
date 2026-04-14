import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token for admin routes
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Intake ────────────────────────────────────────────────────
export const submitRequest = (data: object) =>
  api.post('/intake/requests', data)

export const resendOtp = (requestId: string) =>
  api.post(`/intake/requests/${requestId}/resend-otp`)

export const verifyOtp = (requestId: string, otpCode: string) =>
  api.post(`/intake/requests/${requestId}/verify-otp`, { request_id: requestId, otp_code: otpCode })

export const getRequestStatus = (reference: string) =>
  api.get(`/intake/requests/${reference}/status`)

// ── Admin ─────────────────────────────────────────────────────
export const adminLogin = (email: string, password: string) =>
  api.post('/auth/login', { email, password })

export const getQueue = (params?: object) =>
  api.get('/admin/queue', { params })

export const getRequestDetail = (id: string) =>
  api.get(`/admin/requests/${id}`)

export const getAuditLog = (id: string) =>
  api.get(`/admin/requests/${id}/audit-log`)

export const getWorkflow = (id: string) =>
  api.get(`/admin/requests/${id}/workflow`)

export const advanceWorkflow = (id: string, notes?: string) =>
  api.post(`/admin/requests/${id}/advance`, null, { params: { notes } })

export const rejectRequest = (id: string, reason: string, partial = false) =>
  api.post(`/admin/requests/${id}/reject`, null, { params: { reason, partial } })

export const runQaCheck = (id: string) =>
  api.get(`/admin/requests/${id}/qa-check`)

export const generateDraft = (id: string) =>
  api.post(`/admin/requests/${id}/generate-draft`)

export const approveDraft = (id: string, draftId: string, editedText?: string) =>
  api.post(`/admin/requests/${id}/approve-draft/${draftId}`, null,
    { params: { edited_text: editedText } })

export const deliverRequest = (id: string, method = 'email') =>
  api.post(`/admin/requests/${id}/deliver`, null, { params: { method } })

export default api
