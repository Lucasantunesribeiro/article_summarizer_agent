import { useQuery } from '@tanstack/react-query'
import { pollTask } from '../api/tasks'

export function usePolling(taskId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['task', taskId],
    queryFn: () => pollTask(taskId!),
    enabled: enabled && taskId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.task?.status
      if (!status || status === 'done' || status === 'failed' || status === 'error') {
        return false
      }
      return 2000
    },
  })
}
