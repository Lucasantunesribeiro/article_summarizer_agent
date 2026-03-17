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
      const msg = err instanceof Error ? err.message : 'Falha ao enviar tarefa. Tente novamente.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-6 shadow-sm"
    >
      <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-5">
        Resumir um Artigo
      </h2>

      {/* URL input */}
      <div className="mb-4">
        <label
          htmlFor="url"
          className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5"
        >
          URL do Artigo
        </label>
        <div className="relative">
          <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-[18px] pointer-events-none">
            link
          </span>
          <input
            id="url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/artigo"
            required
            className="w-full bg-background-light dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition"
          />
        </div>
      </div>

      {/* Method + Length */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label
            htmlFor="method"
            className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5"
          >
            Método
          </label>
          <select
            id="method"
            value={method}
            onChange={(e) => setMethod(e.target.value as 'extractive' | 'generative')}
            className="w-full bg-background-light dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
          >
            <option value="extractive">Extractivo (TF-IDF)</option>
            <option value="generative">Generativo (Gemini)</option>
          </select>
        </div>
        <div>
          <label
            htmlFor="length"
            className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5"
          >
            Tamanho
          </label>
          <select
            id="length"
            value={length}
            onChange={(e) => setLength(e.target.value as 'short' | 'medium' | 'long')}
            className="w-full bg-background-light dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
          >
            <option value="short">Curto</option>
            <option value="medium">Médio</option>
            <option value="long">Longo</option>
          </select>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 px-3 py-2.5 mb-4"
        >
          <span className="material-symbols-outlined text-red-500 text-[16px] shrink-0">error</span>
          <p className="text-xs text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 h-11 bg-primary text-white rounded-lg text-sm font-bold hover:opacity-90 hover:shadow-lg hover:shadow-primary/20 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      >
        {loading ? (
          <>
            <span className="material-symbols-outlined text-[18px] animate-spin">refresh</span>
            Processando...
          </>
        ) : (
          <>
            Resumir Agora
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </>
        )}
      </button>
    </form>
  )
}
