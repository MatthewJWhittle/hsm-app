/**
 * Shared helpers for admin background jobs: 202 Accepted → poll job → refetch resource.
 */
import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { isRecord } from './jsonGuards'

export type AdminJobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export type AdminJobError = { code: string; message: string; detail?: string | null }

export type AdminJob = {
  id: string
  kind: string
  status: AdminJobStatus
  input: Record<string, unknown>
  error: AdminJobError | null
  /** Present when the API persists retry metadata (background jobs). */
  attempt_count?: number
  last_error_at?: string | null
  last_error_code?: string | null
}

function isAdminJobStatus(value: string): value is AdminJobStatus {
  return value === 'queued' || value === 'running' || value === 'succeeded' || value === 'failed'
}

function parseAdminJob(raw: unknown): AdminJob | null {
  if (!isRecord(raw)) return null
  if (typeof raw.id !== 'string' || typeof raw.kind !== 'string' || typeof raw.status !== 'string') {
    return null
  }
  if (!isAdminJobStatus(raw.status)) return null
  const inputRaw = raw.input
  const input: Record<string, unknown> =
    inputRaw !== undefined && inputRaw !== null && isRecord(inputRaw) ? inputRaw : {}
  let error: AdminJobError | null = null
  if (raw.error !== undefined && raw.error !== null) {
    if (!isRecord(raw.error)) return null
    const { code, message, detail } = raw.error
    if (typeof code !== 'string' || typeof message !== 'string') return null
    if (
      detail !== undefined &&
      detail !== null &&
      typeof detail !== 'string'
    ) {
      return null
    }
    error = { code, message, ...(detail !== undefined ? { detail } : {}) }
  }
  const out: AdminJob = {
    id: raw.id,
    kind: raw.kind,
    status: raw.status,
    input,
    error,
  }
  if (typeof raw.attempt_count === 'number' && Number.isFinite(raw.attempt_count)) {
    out.attempt_count = raw.attempt_count
  }
  if (raw.last_error_at === null) {
    out.last_error_at = null
  } else if (typeof raw.last_error_at === 'string') {
    out.last_error_at = raw.last_error_at
  }
  if (raw.last_error_code === null) {
    out.last_error_code = null
  } else if (typeof raw.last_error_code === 'string') {
    out.last_error_code = raw.last_error_code
  }
  return out
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export async function fetchAdminJob(params: { token: string; jobId: string }): Promise<AdminJob> {
  const r = await fetch(`${apiBase()}/jobs/${encodeURIComponent(params.jobId)}`, {
    headers: { Authorization: `Bearer ${params.token}` },
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const job = parseAdminJob(raw)
  if (job === null) throw new Error('Invalid job response')
  return job
}

export async function pollAdminJobUntilTerminal(params: {
  token: string
  jobId: string
  onStatus?: (status: AdminJobStatus) => void
  signal?: AbortSignal
  /** Shown if polling exceeds the deadline (defaults to a generic message). */
  timeoutMessage?: string
}): Promise<AdminJob> {
  let waitMs = 500
  const maxWaitMs = 10_000
  const deadline = Date.now() + 45 * 60 * 1000
  const timeoutMsg =
    params.timeoutMessage?.trim() ||
    'Background job timed out while waiting for completion.'
  while (Date.now() < deadline) {
    if (params.signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }
    const job = await fetchAdminJob({ token: params.token, jobId: params.jobId })
    params.onStatus?.(job.status)
    if (job.status === 'succeeded' || job.status === 'failed') {
      return job
    }
    await delay(waitMs)
    waitMs = Math.min(maxWaitMs, Math.floor(waitMs * 1.5))
  }
  throw new Error(timeoutMsg)
}

/** Shared by 202 → poll → refetch flows when the job document reports `failed`. */
export function throwIfFailedAdminJob(job: AdminJob, fallbackMessage: string): void {
  if (job.status === 'failed') {
    throw new Error(job.error?.message?.trim() || fallbackMessage)
  }
}

/** Poll until terminal, throw if the job failed, then run ``onSuccess`` (e.g. refetch entity). */
export async function waitForBackgroundJobThen<T>(
  poll: {
    token: string
    jobId: string
    onStatus?: (status: AdminJobStatus) => void
    signal?: AbortSignal
    timeoutMessage?: string
  },
  fallbackOnFailure: string,
  onSuccess: () => Promise<T>,
): Promise<T> {
  const job = await pollAdminJobUntilTerminal(poll)
  throwIfFailedAdminJob(job, fallbackOnFailure)
  return onSuccess()
}

export function parseJobAcceptedResourceIds(raw: unknown): {
  job_id: string
  project_id: string | null
  model_id: string | null
} | null {
  if (!isRecord(raw) || typeof raw.job_id !== 'string') return null
  return {
    job_id: raw.job_id,
    project_id: typeof raw.project_id === 'string' ? raw.project_id : null,
    model_id: typeof raw.model_id === 'string' ? raw.model_id : null,
  }
}
