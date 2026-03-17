import { useState, useEffect } from 'react'

export interface AuthState {
  isAuthenticated: boolean
  username: string | null
  role: string | null
}

export function useAuth(): AuthState {
  const [auth, setAuth] = useState<AuthState>({
    isAuthenticated: false,
    username: null,
    role: null,
  })

  useEffect(() => {
    // Read JWT claims from cookies (set by Flask-JWT-Extended)
    const cookies = document.cookie.split('; ').reduce(
      (acc: Record<string, string>, c) => {
        const [k, v] = c.split('=')
        acc[k] = v
        return acc
      },
      {}
    )

    const hasAccessToken = 'access_token_cookie' in cookies
    if (hasAccessToken) {
      // Decode JWT payload (base64url, no verification — server validates)
      try {
        const token = cookies['access_token_cookie']
        const payload = JSON.parse(
          atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
        )
        setAuth({
          isAuthenticated: true,
          username: payload.username ?? null,
          role: payload.role ?? null,
        })
      } catch {
        setAuth({ isAuthenticated: false, username: null, role: null })
      }
    }
  }, [])

  return auth
}
