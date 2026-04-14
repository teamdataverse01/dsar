import { useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { verifyOtp, resendOtp } from '../services/api'

export default function VerificationPage() {
  const { requestId } = useParams<{ requestId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { reference, email, devOtp } = (location.state as any) || {}

  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!otp.trim() || otp.length < 6) { setError('Please enter the 6-digit code'); return }
    setLoading(true); setError('')
    try {
      const res = await verifyOtp(requestId!, otp)
      if (res.data.verified) {
        navigate(`/request/status/${reference}`, { state: { justVerified: true } })
      } else {
        setError(res.data.message)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Verification failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setResending(true); setError(''); setMessage('')
    try {
      await resendOtp(requestId!)
      setMessage('A new code has been sent to your email.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend code.')
    } finally {
      setResending(false)
    }
  }

  return (
    <Layout title="Verify Your Identity">
      <div className="max-w-md">
        <div className="card space-y-5">
          {devOtp && (
            <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-4">
              <p className="text-xs font-bold text-yellow-700 uppercase tracking-wide mb-1">Dev mode — OTP visible</p>
              <p className="text-3xl font-mono font-bold text-yellow-900 tracking-widest">{devOtp}</p>
              <p className="text-xs text-yellow-600 mt-1">This banner only appears in development (no email configured).</p>
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              {devOtp
                ? 'No email configured — code shown above for local testing.'
                : <>We sent a 6-digit verification code to <strong>{email || 'your email address'}</strong>.</>}
            </p>
            {reference && (
              <p className="text-xs text-blue-600 mt-1">Reference: <strong>{reference}</strong></p>
            )}
          </div>

          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label className="form-label">Verification code</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                className="form-input text-center text-2xl tracking-widest font-mono"
                placeholder="000000"
                value={otp}
                onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
              />
            </div>

            {error && <p className="text-red-600 text-sm">{error}</p>}
            {message && <p className="text-green-600 text-sm">{message}</p>}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Verifying…' : 'Verify'}
            </button>
          </form>

          <p className="text-sm text-gray-500 text-center">
            Didn't receive the code?{' '}
            <button onClick={handleResend} disabled={resending}
              className="text-brand-600 hover:underline disabled:opacity-50">
              {resending ? 'Sending…' : 'Resend code'}
            </button>
          </p>
        </div>
      </div>
    </Layout>
  )
}
