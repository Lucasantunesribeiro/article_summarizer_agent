import { useState, FormEvent } from 'react'
import { submitTask } from '../api/tasks'

interface Props {
  onTaskSubmitted: (taskId: string) => void
}

export default function SubmitForm({ onTaskSubmitted }: Props) {
  const [url, setUrl] = useState('')
  const [method, setMethod] = useState<'extractive' | 'generative'>('extractive')
  const [length, setLength] = useState<'short' | 'medium' | 'long'>('medium')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await submitTask({ url, method, length })
      onTaskSubmitted(result.task_id)
      setUrl('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit task.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border p-6">
      <h2 className="text-lg font-semibold mb-4">Summarize an Article</h2>

      <div className="mb-4">
        <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
          Article URL
        </label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/article"
          required
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label htmlFor="method" className="block text-sm font-medium text-gray-700 mb-1">
            Method
          </label>
          <select
            id="method"
            value={method}
            onChange={(e) => setMethod(e.target.value as 'extractive' | 'generative')}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="extractive">Extractive (TF-IDF)</option>
            <option value="generative">Generative (Gemini)</option>
          </select>
        </div>
        <div>
          <label htmlFor="length" className="block text-sm font-medium text-gray-700 mb-1">
            Length
          </label>
          <select
            id="length"
            value={length}
            onChange={(e) => setLength(e.target.value as 'short' | 'medium' | 'long')}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="long">Long</option>
          </select>
        </div>
      </div>

      {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Submitting...' : 'Summarize'}
      </button>
    </form>
  )
}
