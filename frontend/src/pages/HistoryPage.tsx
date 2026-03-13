import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listHistory } from '../api/history'
import TaskCard from '../components/TaskCard'

export default function HistoryPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['history', page],
    queryFn: () => listHistory(page),
  })

  if (isLoading) return <p className="text-gray-500">Loading history...</p>
  if (isError) return <p className="text-red-600">Failed to load history. Please log in.</p>

  const { tasks = [], total_pages = 1 } = data ?? {}

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Task History</h1>

      {tasks.length === 0 ? (
        <p className="text-gray-500">No tasks yet.</p>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </div>
      )}

      {total_pages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setPage((p) => Math.max(p - 1, 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm border rounded disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-600">
            {page} / {total_pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(p + 1, total_pages))}
            disabled={page === total_pages}
            className="px-3 py-1.5 text-sm border rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
