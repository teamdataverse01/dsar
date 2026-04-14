import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import { getRequestStatus } from '../services/api'

const STATUS_LABELS: Record<string, { label: string; color: string; description: string }> = {
  submitted:            { label: 'Submitted',          color: 'bg-gray-100 text-gray-700',    description: 'Your request has been received.' },
  verification_pending: { label: 'Awaiting Verification', color: 'bg-yellow-100 text-yellow-800', description: 'Please verify your identity via email.' },
  verified:             { label: 'Verified',           color: 'bg-blue-100 text-blue-800',    description: 'Your identity has been confirmed. We are now processing your request.' },
  data_lookup:          { label: 'Processing',         color: 'bg-blue-100 text-blue-800',    description: 'We are searching our systems for your data.' },
  review_ready:         { label: 'Under Review',       color: 'bg-purple-100 text-purple-800', description: 'Your request is being reviewed by our team.' },
  escalated:            { label: 'Escalated',          color: 'bg-orange-100 text-orange-800', description: 'Your request has been referred to our senior team for review.' },
  approved:             { label: 'Approved',           color: 'bg-green-100 text-green-800',  description: 'Your request has been approved and is being prepared for delivery.' },
  delivered:            { label: 'Delivered',          color: 'bg-green-100 text-green-800',  description: 'Your response has been sent. Please check your email.' },
  completed:            { label: 'Completed',          color: 'bg-green-100 text-green-800',  description: 'Your request has been fully processed.' },
  rejected:             { label: 'Rejected',           color: 'bg-red-100 text-red-800',      description: 'Your request could not be fulfilled. Please check your email for details.' },
  partial_rejection:    { label: 'Partial Response',   color: 'bg-yellow-100 text-yellow-800', description: 'We were able to partially fulfil your request. Please check your email.' },
}

export default function RequestStatus() {
  const { reference } = useParams<{ reference: string }>()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!reference) return
    getRequestStatus(reference)
      .then(r => setData(r.data))
      .catch(() => setError('Request not found. Please check your reference number.'))
      .finally(() => setLoading(false))
  }, [reference])

  const statusInfo = data ? STATUS_LABELS[data.status] : null

  return (
    <Layout title="Request Status">
      <div className="max-w-lg">
        {loading && <p className="text-gray-500">Loading…</p>}
        {error && <div className="card bg-red-50 border-red-200 text-red-700">{error}</div>}
        {data && (
          <div className="card space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">Reference</p>
                <p className="font-mono font-bold text-lg text-brand-800">{data.reference}</p>
              </div>
              {statusInfo && (
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusInfo.color}`}>
                  {statusInfo.label}
                </span>
              )}
            </div>

            {statusInfo && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-700">{statusInfo.description}</p>
              </div>
            )}

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-500">Request type</dt>
                <dd className="font-medium capitalize">{data.request_type?.replace('_', ' ')}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Risk level</dt>
                <dd className="font-medium capitalize">{data.risk_tier || '—'}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Submitted</dt>
                <dd className="font-medium">{new Date(data.submitted_at).toLocaleDateString()}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Due by</dt>
                <dd className="font-medium">{data.due_date ? new Date(data.due_date).toLocaleDateString() : '—'}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Identity verified</dt>
                <dd className={`font-medium ${data.is_verified ? 'text-green-600' : 'text-yellow-600'}`}>
                  {data.is_verified ? 'Yes' : 'Pending'}
                </dd>
              </div>
            </dl>

            <p className="text-xs text-gray-400">
              For queries, contact us quoting reference <strong>{data.reference}</strong>.
            </p>
          </div>
        )}
      </div>
    </Layout>
  )
}
