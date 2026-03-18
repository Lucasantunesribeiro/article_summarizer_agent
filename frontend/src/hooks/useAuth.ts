import { useState, useEffect } from 'react'
import { getCurrentUser } from '../api/auth'

export interface AuthState {
  isAuthenticated: boolean
  loading: boolean
  username: string | null
  role: string | null
}

export function useAuth(): AuthState {
  const [auth, setAuth] = useState<AuthState>({
    isAuthenticated: false,
    loading: true,
    username: null,
    role: null,
  })

  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        setAuth({ isAuthenticated: true, loading: false, username: user.username, role: user.role })
      })
      .catch(() => {
        setAuth({ isAuthenticated: false, loading: false, username: null, role: null })
      })
  }, [])

  return auth
}
