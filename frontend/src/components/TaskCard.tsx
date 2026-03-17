import type { Task } from '../api/tasks'

const STATUS_CONFIG: Record<
  string,
  { label: string; classes: string; pulse?: boolean; dot: string }
> = {
  queued: {
    label: 'Pendente',
    classes: 'bg-blue-500/10 border-blue-500/20 text-blue-600 dark:text-blue-400',
    pulse: true,
    dot: 'bg-blue-500',
  },
  processing: {
    label: 'Processando',
    classes: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-600 dark:text-yellow-400',
    pulse: true,
    dot: 'bg-yellow-500',
  },
  done: {
    label: 'Concluído',
    classes: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400',
    dot: 'bg-emerald-500',
  },
  failed: {
    label: 'Falha',
    classes: 'bg-red-500/10 border-red-500/20 text-red-600 dark:text-red-400',
    dot: 'bg-red-500',
  },
  error: {
    label: 'Erro',
    classes: 'bg-red-500/10 border-red-500/20 text-red-600 dark:text-red-400',
    dot: 'bg-red-500',
  },
}

interface Props {
  task: Task
}

export default function TaskCard({ task }: Props) {
  const cfg = STATUS_CONFIG[task.status] ?? {
    label: task.status,
    classes: 'bg-slate-100 border-slate-200 text-slate-600 dark:text-slate-400',
    dot: 'bg-slate-400',
  }

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-3">
        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 truncate flex-1">
          {task.url}
        </p>
        <span
          className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium whitespace-nowrap shrink-0 ${cfg.classes}`}
        >
          <span className={`size-1.5 rounded-full ${cfg.dot} ${cfg.pulse ? 'animate-pulse' : ''}`} />
          {cfg.label}
        </span>
      </div>

      {(task.status === 'processing' || task.status === 'queued') && (
        <div className="mt-2">
          <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-primary h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.max(task.progress, 3)}%` }}
            />
          </div>
          {task.message && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5">{task.message}</p>
          )}
        </div>
      )}

      {task.status === 'done' && task.summary && (
        <p className="text-sm text-slate-700 dark:text-slate-300 mt-2 line-clamp-3 leading-relaxed">
          {task.summary}
        </p>
      )}

      {(task.status === 'failed' || task.status === 'error') && task.error && (
        <p className="text-xs text-red-600 dark:text-red-400 mt-2">{task.error}</p>
      )}
    </div>
  )
}
