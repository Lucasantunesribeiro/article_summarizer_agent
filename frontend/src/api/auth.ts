import { apiClient } from './client'

export interface AuthUser {
  id: string
  username: string
  role: string
}

export async function login(username: string, password: string): Promise<void> {
  await apiClient.post('/api/auth/login', { username, password })
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout')
}

export async function getCurrentUser(): Promise<AuthUser> {
  const res = await apiClient.get('/api/auth/me')
  return res.data.user as AuthUser
}

export async function refreshToken(): Promise<string> {
  const res = await apiClient.post('/api/auth/refresh')
  return res.data.access_token as string
}

export async function register(username: string, password: string): Promise<void> {
  await apiClient.post('/api/auth/register', { username, password })
}
