import { apiClient } from './client'

export interface SubmitTaskParams {
  url: string
  method?: 'extractive' | 'generative'
  length?: 'short' | 'medium' | 'long'
  idempotencyKey?: string
}

export interface Task {
  id: string
  status: string
  progress: number
  message: string | null
  url: string
  method: string
  length: string
  created_at: string
  finished_at: string | null
  summary: string | null
  error: string | null
  result?: {
    summary: string
    method_used: string
    execution_time: number
    statistics: Record<string, unknown>
    files_created: Record<string, string>
  }
}

export async function submitTask(params: SubmitTaskParams): Promise<{ task_id: string }> {
  const headers: Record<string, string> = {}
  if (params.idempotencyKey) {
    headers['X-Idempotency-Key'] = params.idempotencyKey
  }
  const { data } = await apiClient.post(
    '/api/sumarizar',
    {
      url: params.url,
      method: params.method ?? 'extractive',
      length: params.length ?? 'medium',
    },
    { headers }
  )
  return data
}

export async function pollTask(taskId: string): Promise<{ task: Task }> {
  const { data } = await apiClient.get(`/api/tarefa/${taskId}`)
  return data
}

export async function downloadFile(taskId: string, fmt: string): Promise<Blob> {
  const { data } = await apiClient.get(`/api/download/${taskId}/${fmt}`, {
    responseType: 'blob',
  })
  return data
}
