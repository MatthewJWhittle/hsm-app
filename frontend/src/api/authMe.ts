import { apiBase } from '../utils/apiBase'

export type AuthMe = {
  uid: string
  email: string | null
}

export async function fetchAuthMe(idToken: string): Promise<AuthMe> {
  const base = apiBase()
  const r = await fetch(`${base}/auth/me`, {
    headers: { Authorization: `Bearer ${idToken}` },
  })
  if (r.status === 401) {
    throw new Error('Unauthorized')
  }
  if (!r.ok) {
    throw new Error(r.statusText || String(r.status))
  }
  const raw: unknown = await r.json()
  if (!raw || typeof raw !== 'object') {
    throw new Error('Invalid /auth/me response')
  }
  const o = raw as Record<string, unknown>
  const uid = o.uid
  if (typeof uid !== 'string') {
    throw new Error('Invalid /auth/me response')
  }
  const email = o.email
  return {
    uid,
    email: typeof email === 'string' ? email : null,
  }
}
