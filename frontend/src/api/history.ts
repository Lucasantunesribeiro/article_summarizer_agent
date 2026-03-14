import { apiClient } from './client'
import type { Task } from './tasks'

export interface HistoryResponse {
  tasks: Task[]
  page: number
  per_page: number
  total: number
  total_pages: number
}

export async function listHistory(page = 1, perPage = 20): Promise<HistoryResponse> {
  const { data } = await apiClient.get('/api/historico', {
    params: { page, per_page: perPage },
  })
  return data
}

export async function getStats(): Promise<Record<string, number>> {
  const { data } = await apiClient.get('/api/estatisticas')
  return data.stats
}
