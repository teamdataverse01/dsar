import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getRequestDetail, getAuditLog, getWorkflow,
  advanceWorkflow, rejectRequest, runQaCheck,
  generateDraft, approveDraft, deliverRequest
} from '../../services/api'
import clsx from 'clsx'

const RISK_BADGE: Record<string, string> = {
  low: 'badge-low', medium: 'badge-medium', high: 'badge-high', critical: 'badge-critical',
}

export default function AdminRequestDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [request, setRequest] = useState<any>(null)
  const [auditLog, setAuditLog] = useState<any[]>([])
  const [workflow, setWorkflow] = useState<any[]>([])
  const [draft, setDraft] = useState<any>(null)
  const [qa, setQa] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState('')
  const [tab, setTab] = useState<'overview' | 'workflow' | 'audit'>('overview')

  const reload = () => {
    if (!id) return
    Promise.all([getRequestDetail(id), getAuditLog(id), getWorkflow(id)])
      .then(([r, a, w]) => {
        setRequest(r.data); setAuditLog(a.data); setWorkflow(w.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [id])

  const action = async (fn: () => Promise<any>, msg: string) => {
    try { await fn(); setActionMsg(msg); reload() }
    catch (e: any) { setActionMsg(`Error: ${e.response?.data?.detail || e.message}`) }
  }

  const handleQa = async () => {
    const res = await runQaCheck(id!)
    setQa(res.data)
  }

  const handleGenerateDraft = async () => {
    const res = await generateDraft(id!)
    setDraft(res.data)
  }

  if (loading) return <div className="p-8 text-gray-500">Loading…</div>
  if (!request) return <div className="p-8 text-red-500">Request not found</div>

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-brand-900 text-white">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/admin/queue')} className="text-brand-200 hover:text-white text-sm">← Queue</button>
          <span className="font-semibold">Request {request.reference}</span>
          {request.risk_tier && <span className={RISK_BADGE[request.risk_tier]}>{request.risk_tier}</span>}
          {request.is_escalated && <span className="badge-high">Escalated</span>}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {actionMsg && (
          <div className={clsx('p-3 rounded-lg text-sm', actionMsg.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700')}>
            {actionMsg}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-200">
          {(['overview', 'workflow', 'audit'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={clsx('px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px',
                tab === t ? 'border-brand-600 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700')}>
              {t}
            </button>
          ))}
        </div>

        {/* Overview tab */}
        {tab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <div className="card">
                <h2 className="font-semibold mb-4">Subject Details</h2>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  {[
                    ['Name', request.subject_full_name],
                    ['Email', request.subject_email],
                    ['Phone', request.subject_phone || '—'],
                    ['Request type', request.request_type?.replace('_', ' ')],
                    ['Status', request.status?.replace('_', ' ')],
                    ['Verified', request.is_verified ? 'Yes' : 'No'],
                    ['Due date', request.due_date ? new Date(request.due_date).toLocaleDateString() : '—'],
                    ['Escalation reason', request.escalation_reason || '—'],
                  ].map(([k, v]) => (
                    <div key={k}><dt className="text-gray-500">{k}</dt><dd className="font-medium capitalize">{v}</dd></div>
                  ))}
                </dl>
              </div>

              {/* AI Draft */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-semibold">Response Draft</h2>
                  <button onClick={handleGenerateDraft} className="btn-secondary text-sm py-1.5">
                    Generate Draft
                  </button>
                </div>
                {draft ? (
                  <div className="space-y-3">
                    <div className="flex gap-3 text-sm">
                      <span className={clsx('font-medium', draft.is_ai_generated ? 'text-purple-600' : 'text-gray-500')}>
                        {draft.is_ai_generated ? 'AI Generated' : 'Template'}
                      </span>
                      {draft.confidence_score != null && (
                        <span className={clsx('font-medium', draft.confidence_score >= 0.75 ? 'text-green-600' : 'text-orange-500')}>
                          Confidence: {Math.round(draft.confidence_score * 100)}%
                        </span>
                      )}
                      {draft.needs_review && <span className="badge-high">Needs Review</span>}
                    </div>
                    <textarea className="form-input text-sm" rows={8} defaultValue={draft.draft_text} id="draft-text" />
                    <button onClick={() => {
                      const text = (document.getElementById('draft-text') as HTMLTextAreaElement).value
                      action(() => approveDraft(id!, draft.draft_id, text), 'Draft approved')
                    }} className="btn-primary text-sm py-1.5">
                      Approve Draft
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">Click "Generate Draft" to create a response draft.</p>
                )}
              </div>

              {/* QA Check */}
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-semibold">QA Check</h2>
                  <button onClick={handleQa} className="btn-secondary text-sm py-1.5">Run QA</button>
                </div>
                {qa && (
                  <div className="space-y-2">
                    <p className={clsx('font-medium text-sm', qa.passed ? 'text-green-600' : 'text-red-600')}>
                      {qa.passed ? 'All checks passed' : `${qa.failures.length} check(s) failed`}
                    </p>
                    {qa.failures.map((f: string, i: number) => (
                      <p key={i} className="text-red-600 text-sm">✗ {f}</p>
                    ))}
                    {qa.warnings.map((w: string, i: number) => (
                      <p key={i} className="text-yellow-600 text-sm">⚠ {w}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action panel */}
            <div className="space-y-4">
              <div className="card">
                <h2 className="font-semibold mb-4">Actions</h2>
                <div className="space-y-2">
                  <button onClick={() => action(() => advanceWorkflow(id!), 'Workflow advanced')}
                    className="btn-primary w-full text-sm">
                    Advance Workflow
                  </button>
                  <button onClick={() => action(() => deliverRequest(id!, 'email'), 'Delivered via email')}
                    className="btn-secondary w-full text-sm">
                    Deliver via Email
                  </button>
                  <button onClick={() => action(() => deliverRequest(id!, 'sharepoint'), 'SharePoint link created')}
                    className="btn-secondary w-full text-sm">
                    Deliver via SharePoint
                  </button>
                  <button onClick={() => {
                    const reason = prompt('Rejection reason:')
                    if (reason) action(() => rejectRequest(id!, reason), 'Request rejected')
                  }} className="w-full px-4 py-2.5 text-sm font-semibold rounded-lg bg-red-50 text-red-700 border border-red-200 hover:bg-red-100">
                    Reject Request
                  </button>
                </div>
              </div>

              <div className="card">
                <h2 className="font-semibold mb-2 text-sm">Current Status</h2>
                <p className="capitalize text-brand-700 font-semibold">{request.status?.replace('_', ' ')}</p>
                <p className="text-xs text-gray-400 mt-1">
                  Submitted {new Date(request.submitted_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Workflow tab */}
        {tab === 'workflow' && (
          <div className="card max-w-2xl">
            <h2 className="font-semibold mb-4">Workflow Timeline</h2>
            <ol className="space-y-4">
              {workflow.map((step: any, i: number) => (
                <li key={i} className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium capitalize">{step.stage?.replace('_', ' ')}</p>
                    {step.notes && <p className="text-xs text-gray-500 mt-0.5">{step.notes}</p>}
                    <p className="text-xs text-gray-400">
                      {step.performed_by} · {step.completed_at ? new Date(step.completed_at).toLocaleString() : '—'}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Audit log tab */}
        {tab === 'audit' && (
          <div className="card">
            <h2 className="font-semibold mb-4">Audit Log</h2>
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-gray-500 uppercase">
                <tr>
                  <th className="pb-2 pr-4">Timestamp</th>
                  <th className="pb-2 pr-4">Action</th>
                  <th className="pb-2 pr-4">Actor</th>
                  <th className="pb-2">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditLog.map((log: any, i: number) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 text-gray-400 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="py-2 pr-4 font-mono text-xs text-gray-700">{log.action}</td>
                    <td className="py-2 pr-4 text-gray-600">{log.actor}</td>
                    <td className="py-2 text-gray-500">{log.detail || '—'}</td>
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
