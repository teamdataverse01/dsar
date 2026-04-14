import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminLogin } from '../../services/api'

export default function AdminLogin() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res = await adminLogin(email, password)
      localStorage.setItem('admin_token', res.data.access_token)
      navigate('/admin/queue')
    } catch {
      setError('Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-brand-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-brand-600 rounded-lg flex items-center justify-center font-bold text-white">DV</div>
          <div>
            <p className="font-bold text-gray-900">DataVerse DSAR</p>
            <p className="text-xs text-gray-500">Admin Portal</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="form-label">Email</label>
            <input type="email" className="form-input" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="form-label">Password</label>
            <input type="password" className="form-input" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
