import { apiClient } from './client'

export interface AuthUser {
  id: string
  username: string
  role: string
}

export async function login(username: string, password: string): Promise<void> {
  await apiClient.post('/auth/login', { username, password })
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}
