import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getQueue } from '../../services/api'
import clsx from 'clsx'

const RISK_BADGE: Record<string, string> = {
  low:      'badge-low',
  medium:   'badge-medium',
  high:     'badge-high',
  critical: 'badge-critical',
}

const STATUS_COLOR: Record<string, string> = {
  submitted:            'text-gray-500',
  verification_pending: 'text-yellow-600',
  verified:             'text-blue-600',
  data_lookup:          'text-blue-600',
  review_ready:         'text-purple-600',
  escalated:            'text-orange-600 font-semibold',
  approved:             'text-green-600',
  delivered:            'text-green-700',
  rejected:             'text-red-600',
  partial_rejection:    'text-yellow-600',
}

export default function AdminQueue() {
  const navigate = useNavigate()
  const [queue, setQueue] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [escalatedOnly, setEscalatedOnly] = useState(false)
  const [riskFilter, setRiskFilter] = useState('')

  const load = () => {
    setLoading(true)
    getQueue({ escalated_only: escalatedOnly, risk_filter: riskFilter || undefined })
      .then(r => setQueue(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [escalatedOnly, riskFilter])

  const logout = () => { localStorage.removeItem('admin_token'); navigate('/admin/login') }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-brand-900 text-white">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center font-bold text-sm">DV</div>
            <span className="font-semibold">DataVerse DSAR — Admin</span>
          </div>
          <button onClick={logout} className="text-sm text-brand-200 hover:text-white">Sign out</button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold text-gray-900">
            Request Queue
            {queue && <span className="ml-2 text-sm font-normal text-gray-500">({queue.total} active)</span>}
          </h1>
          <div className="flex gap-3">
            <select className="form-select text-sm py-1.5 w-40"
              value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
              <option value="">All risk levels</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" checked={escalatedOnly} onChange={e => setEscalatedOnly(e.target.checked)}
                className="rounded border-gray-300 text-brand-600" />
              Escalated only
            </label>
            <button onClick={load} className="btn-secondary text-sm py-1.5">Refresh</button>
          </div>
        </div>

        {loading && <p className="text-gray-500">Loading queue…</p>}

        {queue && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Reference', 'Subject', 'Type', 'Status', 'Risk', 'SLA', 'Escalated'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {queue.items.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No active requests</td></tr>
                )}
                {queue.items.map((item: any) => (
                  <tr key={item.id} onClick={() => navigate(`/admin/requests/${item.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-4 py-3 font-mono font-semibold text-brand-700">{item.reference}</td>
                    <td className="px-4 py-3 text-gray-700">{item.subject_email}</td>
                    <td className="px-4 py-3 capitalize text-gray-700">{item.request_type?.replace('_', ' ')}</td>
                    <td className={clsx('px-4 py-3 capitalize', STATUS_COLOR[item.status] || 'text-gray-600')}>
                      {item.status?.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3">
                      {item.risk_tier
                        ? <span className={RISK_BADGE[item.risk_tier]}>{item.risk_tier}</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                    <td className={clsx('px-4 py-3 font-medium', item.sla_breached ? 'text-red-600' : item.days_remaining != null && item.days_remaining <= 3 ? 'text-orange-500' : 'text-gray-600')}>
                      {item.days_remaining != null
                        ? item.sla_breached ? `Overdue ${Math.abs(item.days_remaining)}d` : `${item.days_remaining}d left`
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {item.is_escalated
                        ? <span className="badge-high">Yes</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
