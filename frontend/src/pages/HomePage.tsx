import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { submitTask } from '../api/tasks'
import { usePolling } from '../hooks/usePolling'

// ─── Helper ────────────────────────────────────────────────────────────────

function estimateReadingTime(text: string | null | undefined): number {
  if (!text) return 0
  const words = text.trim().split(/\s+/).length
  return Math.max(1, Math.ceil(words / 200))
}

function countWords(text: string | null | undefined): number {
  if (!text) return 0
  return text.trim().split(/\s+/).length
}

function handleDownload(taskId: string, fmt: string) {
  const a = document.createElement('a')
  a.href = `/api/download/${taskId}/${fmt}`
  a.download = `resumo-${taskId}.${fmt}`
  a.click()
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function HeroDecorativeCard() {
  return (
    <div className="relative">
      {/* Glow behind card */}
      <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-3xl scale-110 opacity-60" />
      <div className="relative bg-white/5 dark:bg-slate-800/50 border border-white/10 dark:border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="size-8 bg-primary/20 rounded-lg flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-[18px]">description</span>
          </div>
          <div>
            <div className="h-3 w-32 bg-slate-300/30 dark:bg-slate-600/50 rounded-full" />
            <div className="h-2 w-20 bg-slate-300/20 dark:bg-slate-700/50 rounded-full mt-1.5" />
          </div>
          <span className="ml-auto text-xs px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 font-medium">
            Concluído
          </span>
        </div>
        <div className="space-y-2 mb-4">
          <div className="h-2.5 bg-slate-300/20 dark:bg-slate-600/40 rounded-full w-full" />
          <div className="h-2.5 bg-slate-300/20 dark:bg-slate-600/40 rounded-full w-5/6" />
          <div className="h-2.5 bg-slate-300/20 dark:bg-slate-600/40 rounded-full w-4/5" />
          <div className="h-2.5 bg-slate-300/20 dark:bg-slate-600/40 rounded-full w-3/4" />
        </div>
        <div className="flex items-center justify-between pt-3 border-t border-slate-300/10 dark:border-slate-700/40">
          <div className="flex gap-2">
            {['TXT', 'MD', 'JSON'].map((fmt) => (
              <span
                key={fmt}
                className="text-xs px-2.5 py-1 rounded-lg bg-slate-200/40 dark:bg-slate-700/50 text-slate-600 dark:text-slate-300 font-medium"
              >
                {fmt}
              </span>
            ))}
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            <span className="material-symbols-outlined text-[14px] align-middle mr-1">schedule</span>
            1 min leitura
          </span>
        </div>
      </div>
    </div>
  )
}

function HowItWorksSection() {
  const steps = [
    {
      icon: 'cloud_download',
      title: 'Extração',
      description: 'Cole a URL e extraímos o conteúdo completo do artigo automaticamente.',
    },
    {
      icon: 'settings_suggest',
      title: 'Processamento',
      description: 'O texto é processado, limpo e preparado para análise com IA.',
    },
    {
      icon: 'description',
      title: 'Resumo',
      description: 'Receba um resumo preciso com os pontos principais destacados.',
    },
  ]

  return (
    <section className="py-16 md:py-24 border-t border-slate-200 dark:border-slate-800/60">
      <div className="max-w-[1200px] mx-auto px-6">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black text-slate-900 dark:text-white mb-3">
            Como Funciona
          </h2>
          <p className="text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            Três etapas simples para ter o resumo do artigo que você precisa.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div
              key={step.title}
              className="flex flex-col items-center text-center group"
            >
              <div className="relative mb-5">
                <div className="size-14 bg-primary/10 dark:bg-primary/20 rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition">
                  <span className="material-symbols-outlined text-primary text-[26px]">
                    {step.icon}
                  </span>
                </div>
                <span className="absolute -top-2 -right-2 size-5 bg-primary rounded-full flex items-center justify-center text-white text-[10px] font-bold">
                  {i + 1}
                </span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function CtaSection({ onScrollToForm }: { onScrollToForm: () => void }) {
  return (
    <section className="py-12 md:py-16">
      <div className="max-w-[1200px] mx-auto px-6">
        <div className="relative bg-primary rounded-3xl p-12 md:p-20 overflow-hidden text-center">
          {/* Decorative blobs */}
          <div className="absolute -top-12 -left-12 w-48 h-48 bg-white/10 rounded-full blur-2xl pointer-events-none" />
          <div className="absolute -bottom-12 -right-12 w-64 h-64 bg-white/5 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <h2 className="text-3xl md:text-4xl font-black text-white mb-4">
              Pronto para economizar tempo?
            </h2>
            <p className="text-white/70 mb-8 max-w-md mx-auto">
              Comece agora e transforme qualquer artigo em um resumo inteligente em segundos.
            </p>
            <button
              onClick={onScrollToForm}
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-primary font-bold rounded-xl hover:shadow-xl hover:shadow-black/20 transition-all text-sm"
            >
              <span className="material-symbols-outlined text-[18px]">rocket_launch</span>
              Começar Agora
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Landing page (form + hero) ─────────────────────────────────────────────

interface LandingProps {
  onTaskSubmitted: (taskId: string, url: string) => void
}

function LandingView({ onTaskSubmitted }: LandingProps) {
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
      onTaskSubmitted(result.task_id, url)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Falha ao enviar tarefa. Tente novamente.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const scrollToForm = () => {
    document.getElementById('url-form')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <>
      {/* Hero */}
      <section className="max-w-[1200px] mx-auto px-6 py-12 md:py-24">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left col */}
          <div>
            <p className="text-primary uppercase tracking-widest text-xs font-bold mb-4">
              Extração por IA
            </p>
            <h1 className="text-5xl md:text-6xl font-black text-slate-900 dark:text-white leading-[1.05] tracking-tight mb-6">
              Resuma qualquer artigo em{' '}
              <span className="text-primary">segundos</span>
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-lg leading-relaxed mb-8">
              Cole a URL de qualquer artigo e receba um resumo inteligente com os pontos principais
              destacados. Suporte a TF-IDF extractivo e Gemini generativo.
            </p>

            {/* URL form card */}
            <div
              id="url-form"
              className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 shadow-xl shadow-slate-200/60 dark:shadow-black/30 p-5"
            >
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-[20px] pointer-events-none">
                    link
                  </span>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Cole a URL do artigo aqui..."
                    required
                    aria-label="URL do artigo"
                    className="w-full bg-background-light dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg pl-11 pr-4 py-3.5 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                      Método
                    </label>
                    <select
                      value={method}
                      onChange={(e) => setMethod(e.target.value as 'extractive' | 'generative')}
                      className="w-full bg-background-light dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary/40 transition"
                    >
                      <option value="extractive">Extractivo (TF-IDF)</option>
                      <option value="generative">Generativo (Gemini)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                      Tamanho
                    </label>
                    <select
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
                    className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 px-3 py-2.5"
                  >
                    <span className="material-symbols-outlined text-red-500 text-[16px] shrink-0">
                      error
                    </span>
                    <p className="text-xs text-red-700 dark:text-red-400">{error}</p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 h-12 bg-primary text-white rounded-lg text-sm font-bold hover:opacity-90 hover:shadow-lg hover:shadow-primary/20 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {loading ? (
                    <>
                      <span className="material-symbols-outlined text-[18px] animate-spin">
                        refresh
                      </span>
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
            </div>

            {/* Note */}
            <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500">
              <span className="material-symbols-outlined text-[14px]">info</span>
              Suporta Medium, Substack, portais de notícias e mais.
            </p>
          </div>

          {/* Right col — decorative card (hidden on mobile) */}
          <div className="hidden lg:block">
            <HeroDecorativeCard />
          </div>
        </div>
      </section>

      <HowItWorksSection />
      <CtaSection onScrollToForm={scrollToForm} />
    </>
  )
}

// ─── Processing view ─────────────────────────────────────────────────────────

interface ProcessingViewProps {
  url: string
  progress: number
  message: string | null
}

function ProcessingView({ url, progress, message }: ProcessingViewProps) {
  return (
    <div className="max-w-[1200px] mx-auto px-6 py-12">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-8">
        <Link to="/" className="hover:text-primary transition">
          Painel
        </Link>
        <span className="mx-1">/</span>
        <span className="text-slate-900 dark:text-white font-medium">Processando Resumo</span>
      </nav>

      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-8 shadow-lg">
          <div className="flex items-center gap-4 mb-6">
            <div className="size-12 bg-primary/10 rounded-xl flex items-center justify-center animate-pulse">
              <span className="material-symbols-outlined text-primary text-[24px]">
                auto_awesome
              </span>
            </div>
            <div>
              <h2 className="font-bold text-slate-900 dark:text-white">Processando artigo...</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">
                {url}
              </p>
            </div>
            <span className="ml-auto inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 font-medium animate-pulse">
              <span className="size-1.5 bg-blue-500 rounded-full" />
              Processando
            </span>
          </div>

          {/* Progress bar */}
          <div className="mb-3">
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-2">
              <span>{message ?? 'Aguardando...'}</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-500 relative overflow-hidden"
                style={{ width: `${Math.max(progress, 5)}%` }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-400 dark:text-slate-500 text-center mt-4">
            Isso pode levar alguns segundos dependendo do tamanho do artigo.
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── Result view ─────────────────────────────────────────────────────────────

interface ResultViewProps {
  taskId: string
  url: string
  summary: string | null
  filesCreated: Record<string, string> | undefined
  statistics: Record<string, unknown> | undefined
  onNewQuery: () => void
}

function ResultView({
  taskId,
  url,
  summary,
  filesCreated: _filesCreated,
  statistics,
  onNewQuery,
}: ResultViewProps) {
  const [activeTab, setActiveTab] = useState<'summary' | 'original'>('summary')

  const wordCount = countWords(summary)
  const readingTime = estimateReadingTime(summary)

  // Split summary into sentences for key findings bullets
  const sentences = summary
    ? summary
        .split(/(?<=[.!?])\s+/)
        .map((s) => s.trim())
        .filter((s) => s.length > 40)
        .slice(0, 4)
    : []

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-10">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-6">
        <Link to="/" className="hover:text-primary transition">
          Painel
        </Link>
        <span className="mx-1">/</span>
        <span className="text-slate-900 dark:text-white font-medium">Resultado do Resumo</span>
      </nav>

      {/* Header row */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-medium">
              <span className="size-1.5 bg-emerald-500 rounded-full" />
              Concluído
            </span>
          </div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white truncate max-w-xl">
            {url}
          </h1>
        </div>

        {/* Progress bar — full when done */}
        <div className="sm:w-48 shrink-0">
          <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Progresso</span>
            <span>100%</span>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
            <div className="bg-emerald-500 h-1.5 rounded-full w-full" />
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Article content — 8 cols */}
        <div className="lg:col-span-8 space-y-4">
          {/* Tabs */}
          <div className="flex gap-1 bg-slate-100 dark:bg-slate-800/50 rounded-lg p-1 w-fit">
            {(['summary', 'original'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  activeTab === tab
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                }`}
              >
                {tab === 'summary' ? 'Resumo' : 'Texto Original'}
              </button>
            ))}
          </div>

          {activeTab === 'summary' ? (
            <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <span className="material-symbols-outlined text-primary text-[22px]">
                  auto_awesome
                </span>
                <h2 className="font-bold text-slate-900 dark:text-white">Visão Executiva</h2>
              </div>
              {summary ? (
                <>
                  <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed mb-6">
                    {summary}
                  </p>
                  {sentences.length > 0 && (
                    <div className="border-t border-slate-100 dark:border-slate-700/50 pt-5">
                      <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                        Pontos-Chave
                      </h3>
                      <ul className="space-y-2.5">
                        {sentences.map((s, i) => (
                          <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300">
                            <span className="size-5 bg-primary/10 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                              <span className="material-symbols-outlined text-primary text-[12px]">
                                check
                              </span>
                            </span>
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-slate-500 dark:text-slate-400 text-sm">
                  Resumo não disponível.
                </p>
              )}
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-6 shadow-sm">
              <p className="text-slate-500 dark:text-slate-400 text-sm">
                O texto original do artigo não está disponível nesta visualização. Faça o download
                do arquivo para acessar o conteúdo completo.
              </p>
            </div>
          )}
        </div>

        {/* Sidebar — 4 cols */}
        <div className="lg:col-span-4 space-y-4">
          {/* Export card */}
          <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">download</span>
              Exportar
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {['txt', 'md', 'json'].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => handleDownload(taskId, fmt)}
                  className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-700 hover:border-primary/40 hover:bg-primary/5 transition text-xs font-medium text-slate-700 dark:text-slate-300"
                >
                  <span className="material-symbols-outlined text-[18px] text-slate-500 dark:text-slate-400">
                    {fmt === 'json' ? 'data_object' : fmt === 'md' ? 'article' : 'text_snippet'}
                  </span>
                  .{fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Stats card */}
          <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/50 p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">analytics</span>
              Estatísticas
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">Tempo de leitura</span>
                <span className="font-medium text-slate-900 dark:text-white">
                  {readingTime} min
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">Palavras no resumo</span>
                <span className="font-medium text-slate-900 dark:text-white">{wordCount}</span>
              </div>
              {statistics && typeof statistics.sentence_count === 'number' && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Frases extraídas</span>
                  <span className="font-medium text-slate-900 dark:text-white">
                    {statistics.sentence_count as number}
                  </span>
                </div>
              )}
              {statistics && typeof statistics.execution_time === 'number' && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Tempo de execução</span>
                  <span className="font-medium text-slate-900 dark:text-white">
                    {(statistics.execution_time as number).toFixed(2)}s
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* New query card */}
          <div className="relative overflow-hidden rounded-xl bg-primary p-5 shadow-lg">
            <div className="absolute -top-4 -right-4 w-24 h-24 bg-white/10 rounded-full blur-xl pointer-events-none" />
            <div className="relative z-10">
              <span className="material-symbols-outlined text-white/70 text-[22px] mb-2 block">
                restart_alt
              </span>
              <h3 className="text-sm font-bold text-white mb-1">Nova consulta</h3>
              <p className="text-xs text-white/70 mb-4">
                Resuma outro artigo a partir do início.
              </p>
              <button
                onClick={onNewQuery}
                className="w-full flex items-center justify-center gap-1.5 h-9 bg-white text-primary rounded-lg text-xs font-bold hover:bg-white/90 transition"
              >
                <span className="material-symbols-outlined text-[16px]">add</span>
                Novo Resumo
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Error view ───────────────────────────────────────────────────────────────

function friendlyError(raw: string): { title: string; detail: string; hint: string | null } {
  const lower = raw.toLowerCase()
  if (lower.includes('insufficient sentences') || lower.includes('not enough')) {
    return {
      title: 'Conteúdo insuficiente',
      detail: 'O artigo não possui texto suficiente para gerar um resumo com o método extrativo.',
      hint: 'Tente novamente com o método Generativo (Gemini) ou verifique se o artigo não exige login para leitura.',
    }
  }
  if (lower.includes('ssrf') || lower.includes('blocked') || lower.includes('private')) {
    return {
      title: 'URL bloqueada',
      detail: 'O endereço aponta para uma rede privada ou é bloqueado por política de segurança.',
      hint: 'Use uma URL pública de um artigo acessível sem autenticação.',
    }
  }
  if (lower.includes('timeout') || lower.includes('timed out')) {
    return {
      title: 'Tempo esgotado',
      detail: 'O servidor demorou muito para responder.',
      hint: 'Tente novamente em alguns segundos.',
    }
  }
  return { title: 'Falha no processamento', detail: raw, hint: null }
}

function ErrorView({ error, url, onRetry }: { error: string; url: string; onRetry: () => void }) {
  const { title, detail, hint } = friendlyError(error)
  return (
    <div className="max-w-[1200px] mx-auto px-6 py-12">
      <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-8">
        <Link to="/" className="hover:text-primary transition">Painel</Link>
        <span className="mx-1">/</span>
        <span className="text-slate-900 dark:text-white font-medium">Erro no Resumo</span>
      </nav>

      <div className="max-w-lg mx-auto bg-white dark:bg-slate-800/50 rounded-xl border border-red-200 dark:border-red-800/40 p-8 text-center shadow-sm">
        <div className="size-14 bg-red-50 dark:bg-red-900/20 rounded-xl flex items-center justify-center mx-auto mb-4">
          {/* SVG fallback — doesn't depend on the icon font */}
          <svg className="w-7 h-7 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
        </div>
        <h2 className="font-bold text-slate-900 dark:text-white text-lg mb-2">{title}</h2>
        <p className="text-sm text-red-600 dark:text-red-400 mb-3">{detail}</p>
        {hint && (
          <p className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 rounded-lg px-4 py-3 mb-4 text-left">
            💡 {hint}
          </p>
        )}
        <p className="text-xs text-slate-400 truncate mb-6 font-mono">{url}</p>
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-lg text-sm font-bold hover:opacity-90 transition"
        >
          Tentar novamente
        </button>
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function HomePage() {
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [submittedUrl, setSubmittedUrl] = useState<string>('')

  const isPolling = activeTaskId !== null
  const { data } = usePolling(activeTaskId, isPolling)

  const task = data?.task
  const isDone = task?.status === 'done'
  const isFailed = task?.status === 'failed' || task?.status === 'error'
  const isProcessing =
    task && (task.status === 'processing' || task.status === 'queued')

  const handleTaskSubmitted = (taskId: string, url: string) => {
    setActiveTaskId(taskId)
    setSubmittedUrl(url)
  }

  const handleNewQuery = () => {
    setActiveTaskId(null)
    setSubmittedUrl('')
  }

  if (!activeTaskId) {
    return <LandingView onTaskSubmitted={handleTaskSubmitted} />
  }

  if (isProcessing || (!task && isPolling)) {
    return (
      <ProcessingView
        url={submittedUrl}
        progress={task?.progress ?? 0}
        message={task?.message ?? null}
      />
    )
  }

  if (isFailed && task) {
    return (
      <ErrorView
        error={task.error ?? 'Erro desconhecido.'}
        url={submittedUrl}
        onRetry={handleNewQuery}
      />
    )
  }

  if (isDone && task) {
    return (
      <ResultView
        taskId={activeTaskId}
        url={submittedUrl || task.url}
        summary={task.result?.summary ?? task.summary}
        filesCreated={task.result?.files_created}
        statistics={task.result?.statistics}
        onNewQuery={handleNewQuery}
      />
    )
  }

  // Fallback — initial load before first poll response
  return (
    <ProcessingView
      url={submittedUrl}
      progress={0}
      message="Aguardando servidor..."
    />
  )
}
