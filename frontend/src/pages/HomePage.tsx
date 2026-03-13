import { useState } from 'react'
import SubmitForm from '../components/SubmitForm'
import TaskCard from '../components/TaskCard'
import { usePolling } from '../hooks/usePolling'

export default function HomePage() {
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const isActive = activeTaskId !== null

  const { data, isLoading } = usePolling(activeTaskId, isActive)

  const task = data?.task
  const isDone =
    task && (task.status === 'done' || task.status === 'failed' || task.status === 'error')

  const handleTaskSubmitted = (taskId: string) => {
    setActiveTaskId(taskId)
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Article Summarizer</h1>
        <p className="text-gray-500 mt-1">
          Enter an article URL to extract and summarize its content.
        </p>
      </div>

      <SubmitForm onTaskSubmitted={handleTaskSubmitted} />

      {activeTaskId && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Current Task</h3>
          {isLoading && !task ? (
            <div className="bg-white rounded-lg border p-4 text-sm text-gray-500">Loading...</div>
          ) : task ? (
            <TaskCard task={task} />
          ) : null}

          {isDone && (
            <div className="flex gap-2 mt-3">
              {task?.result?.files_created &&
                Object.entries(task.result.files_created).map(([fmt]) => (
                  <a
                    key={fmt}
                    href={`/api/download/${activeTaskId}/${fmt}`}
                    className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded"
                  >
                    Download {fmt.toUpperCase()}
                  </a>
                ))}
              <button
                onClick={() => setActiveTaskId(null)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
