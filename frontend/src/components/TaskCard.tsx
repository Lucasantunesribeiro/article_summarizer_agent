import type { Task } from '../api/tasks'

const STATUS_COLORS: Record<string, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  error: 'bg-red-100 text-red-800',
}

interface Props {
  task: Task
}

export default function TaskCard({ task }: Props) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-mono text-gray-500 truncate">{task.url}</p>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${STATUS_COLORS[task.status] ?? 'bg-gray-100 text-gray-700'}`}
        >
          {task.status}
        </span>
      </div>

      {task.status === 'processing' || task.status === 'queued' ? (
        <div className="mt-2">
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">{task.message}</p>
        </div>
      ) : null}

      {task.status === 'done' && task.summary && (
        <p className="text-sm text-gray-700 mt-2 line-clamp-3">{task.summary}</p>
      )}

      {task.status === 'failed' && task.error && (
        <p className="text-sm text-red-600 mt-2">{task.error}</p>
      )}
    </div>
  )
}
