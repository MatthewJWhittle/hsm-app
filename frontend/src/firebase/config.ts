import { getApp, getApps, initializeApp } from 'firebase/app'
import { connectAuthEmulator, getAuth, type Auth } from 'firebase/auth'

let authSingleton: Auth | null = null

export function firebaseWebConfigOk(): boolean {
  return Boolean(
    import.meta.env.VITE_FIREBASE_API_KEY &&
      import.meta.env.VITE_FIREBASE_AUTH_DOMAIN &&
      import.meta.env.VITE_FIREBASE_PROJECT_ID,
  )
}

/** Lazily create Auth so missing env (e.g. CI build) does not throw at module load. */
export function getFirebaseAuth(): Auth {
  if (authSingleton) {
    return authSingleton
  }
  const apiKey = import.meta.env.VITE_FIREBASE_API_KEY
  const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN
  const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID
  if (!apiKey || !authDomain || !projectId) {
    throw new Error('Firebase web config missing (set VITE_FIREBASE_* env vars)')
  }
  const app = getApps().length > 0 ? getApp() : initializeApp({ apiKey, authDomain, projectId })
  authSingleton = getAuth(app)
  if (import.meta.env.VITE_USE_AUTH_EMULATOR === 'true') {
    connectAuthEmulator(authSingleton, 'http://127.0.0.1:9099', { disableWarnings: true })
  }
  return authSingleton
}
