import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateSettings, clearCache, rotateSecret } from '../api/settings'
import { useAuth } from '../hooks/useAuth'

// ─── Feedback toast ───────────────────────────────────────────────────────────

type FeedbackState = { type: 'success' | 'error'; message: string } | null

function Feedback({ state, onDismiss }: { state: FeedbackState; onDismiss: () => void }) {
  if (!state) return null
  const isSuccess = state.type === 'success'
  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${
        isSuccess
          ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800/40 text-emerald-700 dark:text-emerald-400'
          : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/40 text-red-700 dark:text-red-400'
      }`}
    >
      <span className="material-symbols-outlined text-[18px] shrink-0 mt-0.5">
        {isSuccess ? 'check_circle' : 'error'}
      </span>
      <span className="flex-1">{state.message}</span>
      <button
        onClick={onDismiss}
        aria-label="Fechar"
        className="text-current opacity-60 hover:opacity-100 transition"
      >
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  )
}

// ─── Sidebar nav ──────────────────────────────────────────────────────────────

interface SidebarItem {
  label: string
  icon: string
  href: string
  active?: boolean
}

function SidebarNav({ items }: { items: SidebarItem[] }) {
  return (
    <nav className="space-y-1">
      {items.map((item) => (
        <Link
          key={item.label}
          to={item.href}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
            item.active
              ? 'bg-primary/10 text-primary dark:bg-primary/20'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
          {item.label}
        </Link>
      ))}
    </nav>
  )
}

// ─── Setting row ──────────────────────────────────────────────────────────────

function SettingRow({
  label,
  description,
  value,
}: {
  label: string
  description?: string
  value: unknown
}) {
  const display = typeof value === 'boolean' ? (value ? 'Ativado' : 'Desativado') : String(value)
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-100 dark:border-slate-700/50 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900 dark:text-white">{label}</p>
        {description && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{description}</p>
        )}
      </div>
      <span className="ml-4 text-sm font-mono text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700/60 px-2.5 py-1 rounded-lg shrink-0">
        {display}
      </span>
    </div>
  )
}

// ─── Method toggle ────────────────────────────────────────────────────────────

function MethodToggle({
  current,
  onChange,
  loading,
}: {
  current: string | undefined
  onChange: (val: string) => void
  loading: boolean
}) {
  return (
    <div className="flex gap-2 mt-1">
      {['extractive', 'generative'].map((val) => (
        <button
          key={val}
          onClick={() => onChange(val)}
          disabled={loading}
          className={`flex-1 py-2.5 px-4 rounded-xl text-sm font-medium border transition ${
            current === val
              ? 'bg-primary text-white border-primary shadow-sm'
              : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-primary/40'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {val === 'extractive' ? 'Extractivo (TF-IDF)' : 'Generativo (Gemini)'}
        </button>
      ))}
    </div>
  )
}

// ─── Not authenticated state ──────────────────────────────────────────────────

function NotAuthenticatedView() {
  return (
    <div className="max-w-[1200px] mx-auto px-6 py-20 flex flex-col items-center text-center">
      <div className="size-14 bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center mb-4">
        <span className="material-symbols-outlined text-slate-400 text-[28px]">lock</span>
      </div>
      <h1 className="text-2xl font-black text-slate-900 dark:text-white mb-2">
        Acesso Restrito
      </h1>
      <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-sm">
        Você precisa estar autenticado para acessar as configurações do sistema.
      </p>
      <Link
        to="/login"
        className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl text-sm font-bold hover:opacity-90 transition"
      >
        <span className="material-symbols-outlined text-[18px]">login</span>
        Fazer Login
      </Link>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { isAuthenticated, role, username } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [feedback, setFeedback] = useState<FeedbackState>(null)
  const isAdmin = role === 'admin'

  const { data: settings, isLoading: loadingSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    enabled: isAuthenticated,
  })

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setFeedback({ type: 'success', message: 'Configuração atualizada com sucesso.' })
    },
    onError: () => {
      setFeedback({ type: 'error', message: 'Falha ao atualizar configuração.' })
    },
  })

  const handleMethodChange = (val: string) => {
    updateMutation.mutate({ summarization_method: val })
  }

  const handleClearCache = async () => {
    try {
      await clearCache()
      setFeedback({ type: 'success', message: 'Cache do sistema limpo com sucesso.' })
    } catch {
      setFeedback({ type: 'error', message: 'Falha ao limpar o cache.' })
    }
  }

  const handleRotateSecret = async () => {
    const confirmed = window.confirm(
      'Tem certeza? Todas as sessões ativas serão invalidadas após o período de graça.'
    )
    if (!confirmed) return
    try {
      await rotateSecret()
      setFeedback({
        type: 'success',
        message: 'Chave JWT rotacionada. Todas as sessões serão expiradas em breve.',
      })
      setTimeout(() => navigate('/login'), 3000)
    } catch {
      setFeedback({ type: 'error', message: 'Falha ao rotacionar a chave JWT.' })
    }
  }

  if (!isAuthenticated) {
    return <NotAuthenticatedView />
  }

  const sidebarItems: SidebarItem[] = [
    { label: 'Painel', icon: 'dashboard', href: '/' },
    { label: 'Segurança e IAM', icon: 'shield', href: '/configuracoes', active: true },
    { label: 'Logs de Auditoria', icon: 'manage_search', href: '/configuracoes' },
  ]

  const currentMethod =
    settings &&
    (typeof settings['summarization_method'] === 'string'
      ? (settings['summarization_method'] as string)
      : undefined)

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-10">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-slate-900 dark:text-white mb-2">
          Administração
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Configurações de sistema, segurança e gerenciamento de chaves.
        </p>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Sidebar */}
        <aside className="lg:col-span-3">
          <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-4 shadow-sm sticky top-20">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-3 mb-3">
              Navegação
            </p>
            <SidebarNav items={sidebarItems} />
          </div>
        </aside>

        {/* Main content */}
        <div className="lg:col-span-9 space-y-5">
          {/* Feedback */}
          <Feedback state={feedback} onDismiss={() => setFeedback(null)} />

          {/* Runtime Settings */}
          <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700/50 flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">
                settings_suggest
              </span>
              <h2 className="font-bold text-slate-900 dark:text-white">
                Configuração do Sistema
              </h2>
            </div>
            <div className="p-6">
              {loadingSettings ? (
                <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                  <span className="material-symbols-outlined text-[18px] animate-spin">
                    refresh
                  </span>
                  Carregando configurações...
                </div>
              ) : settings ? (
                <>
                  <div className="mb-6">
                    <p className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                      Método de Sumarização
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                      Escolha entre extração baseada em TF-IDF ou geração via Gemini API.
                    </p>
                    <MethodToggle
                      current={currentMethod}
                      onChange={handleMethodChange}
                      loading={updateMutation.isPending}
                    />
                  </div>

                  <div className="space-y-0 divide-y-0">
                    {Object.entries(settings)
                      .filter(([k]) => k !== 'summarization_method')
                      .map(([key, value]) => (
                        <SettingRow key={key} label={key} value={value} />
                      ))}
                  </div>
                </>
              ) : null}
            </div>
          </div>

          {/* JWT Security — admin only */}
          {isAdmin && (
            <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700/50 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-[20px]">
                  key
                </span>
                <h2 className="font-bold text-slate-900 dark:text-white">Segurança JWT</h2>
              </div>
              <div className="p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                      Rotação de Chave Secreta
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Gera uma nova chave JWT. Sessões existentes serão invalidadas após o período
                      de graça configurado.
                    </p>
                  </div>
                  <button
                    onClick={handleRotateSecret}
                    className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-primary/30 bg-primary/5 text-primary text-sm font-medium hover:bg-primary/10 transition"
                  >
                    <span className="material-symbols-outlined text-[16px]">autorenew</span>
                    Rotacionar Agora
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* RBAC / User info */}
          <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700/50 flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-[20px]">
                manage_accounts
              </span>
              <h2 className="font-bold text-slate-900 dark:text-white">Controle de Acesso (RBAC)</h2>
            </div>
            <div className="p-6">
              <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-700/30 rounded-xl border border-slate-100 dark:border-slate-700/40">
                <div className="size-10 bg-primary/10 rounded-full flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary text-[20px]">
                    person
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">
                    {username ?? 'Usuário'}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Sessão autenticada via JWT
                  </p>
                </div>
                <span
                  className={`text-xs px-2.5 py-1 rounded-full font-medium border ${
                    isAdmin
                      ? 'bg-primary/10 text-primary border-primary/20'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600'
                  }`}
                >
                  {role ?? 'user'}
                </span>
              </div>
            </div>
          </div>

          {/* Cache Management — danger zone (admin only) */}
          {isAdmin && (
            <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-rose-200 dark:border-rose-900/40 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-rose-100 dark:border-rose-900/30 flex items-center gap-3 bg-rose-50 dark:bg-rose-900/10">
                <span className="material-symbols-outlined text-rose-500 text-[20px]">
                  warning
                </span>
                <h2 className="font-bold text-rose-700 dark:text-rose-400">
                  Zona de Perigo
                </h2>
              </div>
              <div className="p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                      Limpar Cache do Sistema
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Remove todos os resultados em cache. As próximas requisições para as mesmas
                      URLs serão reprocessadas.
                    </p>
                  </div>
                  <button
                    onClick={handleClearCache}
                    className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-500 text-white text-sm font-medium hover:bg-rose-600 transition"
                  >
                    <span className="material-symbols-outlined text-[16px]">delete_sweep</span>
                    Limpar Cache
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
