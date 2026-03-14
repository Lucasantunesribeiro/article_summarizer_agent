import { apiClient } from './client'

export async function getSettings(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get('/api/settings')
  return data.settings
}

export async function updateSettings(values: Record<string, unknown>): Promise<void> {
  await apiClient.put('/api/settings', { settings: values })
}

export async function clearCache(): Promise<void> {
  await apiClient.post('/api/limpar-cache')
}

export async function rotateSecret(): Promise<void> {
  await apiClient.post('/api/admin/rotate-secret')
}
