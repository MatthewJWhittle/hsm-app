import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from 'firebase/auth'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { getFirebaseAuth, firebaseWebConfigOk } from '../firebase/config'

import { AuthContext } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    if (!firebaseWebConfigOk()) {
      setLoading(false)
      return
    }
    const auth = getFirebaseAuth()
    const unsub = onAuthStateChanged(auth, (u) => {
      if (!u) {
        setUser(null)
        setIsAdmin(false)
        setLoading(false)
        return
      }
      void u.getIdTokenResult().then(
        (r) => {
          setUser(u)
          setIsAdmin(r.claims.admin === true)
          setLoading(false)
        },
        () => {
          setUser(u)
          setIsAdmin(false)
          setLoading(false)
        },
      )
    })
    return () => unsub()
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    await signInWithEmailAndPassword(getFirebaseAuth(), email, password)
  }, [])

  const signUp = useCallback(async (email: string, password: string) => {
    await createUserWithEmailAndPassword(getFirebaseAuth(), email, password)
  }, [])

  const signOutUser = useCallback(async () => {
    await signOut(getFirebaseAuth())
  }, [])

  const getIdToken = useCallback(async (forceRefresh?: boolean) => {
    if (!user) return null
    return user.getIdToken(Boolean(forceRefresh))
  }, [user])

  const value = useMemo(
    () => ({
      user,
      loading,
      isAdmin,
      getIdToken,
      signIn,
      signUp,
      signOutUser,
    }),
    [user, loading, isAdmin, getIdToken, signIn, signUp, signOutUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
