import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { submitRequest } from '../services/api'

const REQUEST_TYPES = [
  { value: 'access', label: 'Access — I want a copy of my data' },
  { value: 'deletion', label: 'Deletion — I want my data deleted' },
  { value: 'modification', label: 'Modification — I want to correct my data' },
  { value: 'stop_processing', label: 'Stop Processing — I want you to stop using my data' },
]

const DATA_CATEGORIES = [
  'Contact information (name, email, phone)',
  'Purchase or transaction history',
  'Marketing preferences',
  'Account details',
  'Communications and correspondence',
  'All data you hold about me',
]

const SENSITIVITY_OPTIONS = [
  { value: 'public', label: 'General / public information' },
  { value: 'internal', label: 'Standard personal data' },
  { value: 'confidential', label: 'Sensitive personal data' },
  { value: 'regulated', label: 'Regulated data (health, financial, legal)' },
]

const PERSONA_OPTIONS = [
  { value: 'general_public', label: 'Member of the public' },
  { value: 'employee', label: 'Current or former employee' },
  { value: 'vulnerable_adult', label: 'Vulnerable adult' },
  { value: 'minor', label: 'Under 18 (parent / guardian submitting)' },
]

const CONTEXT_OPTIONS = [
  { value: 'none', label: 'No special context' },
  { value: 'legal_hold', label: 'Data related to a legal matter' },
  { value: 'active_investigation', label: 'Data subject to an investigation' },
  { value: 'regulatory_inquiry', label: 'Regulatory or compliance inquiry' },
]

interface FormData {
  subject_full_name: string
  subject_email: string
  subject_phone: string
  request_type: string
  data_sensitivity: string
  subject_persona: string
  special_context: string
  data_categories: string[]
}

export default function IntakeForm() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      data_sensitivity: 'internal',
      subject_persona: 'general_public',
      special_context: 'none',
    }
  })

  const onSubmit = async (data: FormData) => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        ...data,
        data_categories: data.data_categories || [],
      }
      const res = await submitRequest(payload)
      navigate(`/request/verify/${res.data.id}`, {
        state: {
          reference: res.data.reference,
          email: data.subject_email,
          devOtp: res.data.dev_otp ?? null,
        }
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Layout title="Submit a Data Request">
      <div className="max-w-2xl">
        <p className="text-gray-600 mb-6">
          Use this form to exercise your data rights. All fields marked * are required.
          You will receive a verification code by email before we process your request.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Personal details */}
          <div className="card space-y-4">
            <h2 className="font-semibold text-gray-800">Your Details</h2>

            <div>
              <label className="form-label">Full name *</label>
              <input className="form-input" {...register('subject_full_name', { required: 'Full name is required' })} />
              {errors.subject_full_name && <p className="text-red-500 text-xs mt-1">{errors.subject_full_name.message}</p>}
            </div>

            <div>
              <label className="form-label">Email address * <span className="text-gray-400 font-normal">(must match the email we hold for you)</span></label>
              <input type="email" className="form-input" {...register('subject_email', { required: 'Email is required' })} />
              {errors.subject_email && <p className="text-red-500 text-xs mt-1">{errors.subject_email.message}</p>}
            </div>

            <div>
              <label className="form-label">Phone number <span className="text-gray-400 font-normal">(optional)</span></label>
              <input type="tel" className="form-input" {...register('subject_phone')} />
            </div>
          </div>

          {/* Request type */}
          <div className="card space-y-4">
            <h2 className="font-semibold text-gray-800">What are you requesting?</h2>

            <div>
              <label className="form-label">Request type *</label>
              <select className="form-select" {...register('request_type', { required: 'Please select a request type' })}>
                <option value="">— Select —</option>
                {REQUEST_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
              {errors.request_type && <p className="text-red-500 text-xs mt-1">{errors.request_type.message}</p>}
            </div>

            <div>
              <label className="form-label">Which data categories does this cover?</label>
              <div className="space-y-2 mt-1">
                {DATA_CATEGORIES.map(cat => (
                  <label key={cat} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input type="checkbox" value={cat} {...register('data_categories')}
                      className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                    {cat}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Context */}
          <div className="card space-y-4">
            <h2 className="font-semibold text-gray-800">Additional Context</h2>

            <div>
              <label className="form-label">Data sensitivity</label>
              <select className="form-select" {...register('data_sensitivity')}>
                {SENSITIVITY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            <div>
              <label className="form-label">I am submitting this as</label>
              <select className="form-select" {...register('subject_persona')}>
                {PERSONA_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            <div>
              <label className="form-label">Special context</label>
              <select className="form-select" {...register('special_context')}>
                {CONTEXT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error}</div>
          )}

          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? 'Submitting…' : 'Submit Request'}
          </button>
        </form>
      </div>
    </Layout>
  )
}
