import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listHistory, getStats } from '../api/history'
import type { Task } from '../api/tasks'

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const configs: Record<string, { label: string; classes: string; pulse?: boolean }> = {
    done: {
      label: 'Sucesso',
      classes: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400',
    },
    pending: {
      label: 'Pendente',
      classes: 'bg-blue-500/10 border-blue-500/20 text-blue-600 dark:text-blue-400',
      pulse: true,
    },
    queued: {
      label: 'Pendente',
      classes: 'bg-blue-500/10 border-blue-500/20 text-blue-600 dark:text-blue-400',
      pulse: true,
    },
    processing: {
      label: 'Processando',
      classes: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-600 dark:text-yellow-400',
      pulse: true,
    },
    failed: {
      label: 'Falha',
      classes: 'bg-red-500/10 border-red-500/20 text-red-600 dark:text-red-400',
    },
    error: {
      label: 'Falha',
      classes: 'bg-red-500/10 border-red-500/20 text-red-600 dark:text-red-400',
    },
  }

  const cfg = configs[status] ?? {
    label: status,
    classes: 'bg-slate-100 border-slate-200 text-slate-600 dark:text-slate-400',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium ${cfg.classes}`}
    >
      <span
        className={`size-1.5 rounded-full ${
          cfg.pulse ? 'animate-pulse' : ''
        } ${
          status === 'done'
            ? 'bg-emerald-500'
            : status === 'failed' || status === 'error'
            ? 'bg-red-500'
            : status === 'processing'
            ? 'bg-yellow-500'
            : 'bg-blue-500'
        }`}
      />
      {cfg.label}
    </span>
  )
}

// ─── Stats card ───────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  colorClass,
}: {
  icon: string
  label: string
  value: string | number
  colorClass: string
}) {
  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`size-10 rounded-xl flex items-center justify-center ${colorClass}`}>
          <span className="material-symbols-outlined text-[20px]">{icon}</span>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
          <p className="text-xl font-black text-slate-900 dark:text-white">{value}</p>
        </div>
      </div>
    </div>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <tr>
      <td colSpan={4}>
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="size-14 bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center mb-4">
            <span className="material-symbols-outlined text-slate-400 text-[28px]">description</span>
          </div>
          <p className="font-semibold text-slate-900 dark:text-white mb-1">Nenhum resumo ainda</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Submeta uma URL na página inicial para começar.
          </p>
        </div>
      </td>
    </tr>
  )
}

// ─── Table row ────────────────────────────────────────────────────────────────

function TaskRow({ task }: { task: Task }) {
  const date = task.created_at
    ? new Date(task.created_at).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'

  const shortId = task.id.slice(0, 8)

  return (
    <tr className="border-t border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
      {/* ID */}
      <td className="px-4 py-3.5">
        <span className="font-mono text-xs text-primary bg-primary/5 px-2 py-1 rounded-lg">
          {shortId}
        </span>
      </td>
      {/* URL */}
      <td className="px-4 py-3.5 max-w-xs">
        <p
          className="text-sm text-slate-700 dark:text-slate-300 truncate"
          title={task.url}
        >
          {task.url}
        </p>
      </td>
      {/* Status */}
      <td className="px-4 py-3.5">
        <StatusBadge status={task.status} />
      </td>
      {/* Date */}
      <td className="px-4 py-3.5 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
        {date}
      </td>
    </tr>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function HistoryPage() {
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['history', page],
    queryFn: () => listHistory(page),
  })

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
  })

  const { tasks = [], total_pages = 1, total = 0 } = data ?? {}

  const doneCount = stats?.done ?? 0
  const failedCount = (stats?.failed ?? 0) + (stats?.error ?? 0)
  const processingCount = (stats?.processing ?? 0) + (stats?.queued ?? 0)

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-10">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-slate-900 dark:text-white mb-2">
          Histórico de Resumos
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Acompanhe todos os artigos que você submeteu para resumo.
        </p>
      </div>

      {/* Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon="summarize"
          label="Total de Resumos"
          value={total}
          colorClass="bg-primary/10 text-primary"
        />
        <StatCard
          icon="check_circle"
          label="Concluídos"
          value={doneCount}
          colorClass="bg-emerald-500/10 text-emerald-500"
        />
        <StatCard
          icon="hourglass_empty"
          label="Em Processamento"
          value={processingCount}
          colorClass="bg-yellow-500/10 text-yellow-500"
        />
        <StatCard
          icon="cancel"
          label="Com Falha"
          value={failedCount}
          colorClass="bg-red-500/10 text-red-500"
        />
      </div>

      {/* Table card */}
      <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 shadow-sm overflow-hidden">
        {/* Table header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700/50">
          <h2 className="font-bold text-slate-900 dark:text-white text-sm">Tarefas Recentes</h2>
          {total > 0 && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {total} tarefa{total !== 1 ? 's' : ''} no total
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16 gap-3 text-slate-500 dark:text-slate-400">
            <span className="material-symbols-outlined text-[20px] animate-spin">refresh</span>
            <span className="text-sm">Carregando histórico...</span>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="material-symbols-outlined text-red-400 text-[32px] mb-3">
              error
            </span>
            <p className="font-semibold text-slate-900 dark:text-white mb-1">
              Falha ao carregar histórico
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Verifique se você está autenticado.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/80 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <th className="px-4 py-3 w-24">ID</th>
                  <th className="px-4 py-3">URL</th>
                  <th className="px-4 py-3 w-32">Status</th>
                  <th className="px-4 py-3 w-40">Data/Hora</th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <EmptyState />
                ) : (
                  tasks.map((task) => <TaskRow key={task.id} task={task} />)
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total_pages > 1 && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-slate-100 dark:border-slate-700/50">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Página {page} de {total_pages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page === 1}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                Anterior
              </button>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, total_pages))}
                disabled={page === total_pages}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Próxima
                <span className="material-symbols-outlined text-[16px]">chevron_right</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
