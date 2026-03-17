import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/auth'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [agreeTerms, setAgreeTerms] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('As senhas não coincidem.')
      return
    }
    if (!agreeTerms) {
      setError('Você precisa aceitar os termos para continuar.')
      return
    }

    setLoading(true)
    try {
      await register(username, password)
      navigate('/')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      setError(msg ?? 'Não foi possível criar a conta. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark flex flex-col">
      {/* Top gradient bar */}
      <div className="fixed top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary to-transparent opacity-50 z-50" />

      {/* Background glow blobs */}
      <div className="fixed -bottom-24 -left-24 w-64 h-64 bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed -top-24 -right-24 w-64 h-64 bg-primary/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Minimal header */}
      <header className="flex items-center justify-between px-6 py-4 relative z-10">
        <Link to="/" className="flex items-center gap-3">
          <div className="size-8 bg-primary rounded-lg flex items-center justify-center text-white shrink-0">
            <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
          </div>
          <span className="text-slate-900 dark:text-white text-lg font-bold tracking-[-0.015em]">
            Sumarizador.ai
          </span>
        </Link>
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span className="hidden sm:block">Já possui uma conta?</span>
          <Link to="/login" className="text-primary font-medium hover:opacity-80 transition">
            Entre aqui
          </Link>
        </div>
      </header>

      {/* Centered form */}
      <main className="flex-1 flex items-center justify-center px-4 py-12 relative z-10">
        <div className="w-full max-w-[440px]">
          {/* Title */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-black text-slate-900 dark:text-white mb-2">
              Criar conta
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              Comece a resumir artigos em segundos
            </p>
          </div>

          {/* Card */}
          <div className="bg-white dark:bg-slate-900/60 rounded-xl border border-slate-200 dark:border-slate-800 p-8 shadow-xl shadow-slate-200/50 dark:shadow-black/30 backdrop-blur-sm">
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Username */}
              <div>
                <label
                  htmlFor="username"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                >
                  Usuário
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-[20px] pointer-events-none">
                    person
                  </span>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    autoComplete="username"
                    placeholder="seu.usuario"
                    className="w-full bg-background-light dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl pl-11 pr-4 py-4 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                >
                  Senha
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-[20px] pointer-events-none">
                    lock
                  </span>
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder="••••••••"
                    className="w-full bg-background-light dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl pl-11 pr-11 py-4 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      {showPassword ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              {/* Confirm password */}
              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2"
                >
                  Confirmar senha
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-[20px] pointer-events-none">
                    lock_reset
                  </span>
                  <input
                    id="confirmPassword"
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder="••••••••"
                    className="w-full bg-background-light dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl pl-11 pr-4 py-4 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition"
                  />
                </div>
              </div>

              {/* Terms */}
              <label className="flex items-start gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) => setAgreeTerms(e.target.checked)}
                  className="mt-0.5 size-4 accent-primary rounded"
                />
                <span className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Concordo com os{' '}
                  <span className="text-primary font-medium">Termos de Uso</span> e a{' '}
                  <span className="text-primary font-medium">Política de Privacidade</span>.
                </span>
              </label>

              {/* Error */}
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 px-4 py-3"
                >
                  <span className="material-symbols-outlined text-red-500 text-[18px] shrink-0 mt-0.5">
                    error
                  </span>
                  <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-14 bg-primary text-white rounded-xl text-sm font-bold hover:opacity-90 hover:shadow-lg hover:shadow-primary/20 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="material-symbols-outlined text-[18px] animate-spin">
                      refresh
                    </span>
                    Criando conta...
                  </span>
                ) : (
                  'Criar conta'
                )}
              </button>
            </form>

            {/* JWT badge */}
            <div className="mt-6 flex justify-center">
              <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
                <span className="material-symbols-outlined text-[16px]">verified_user</span>
                Autenticação JWT segura
              </span>
            </div>
          </div>

          {/* Footer link */}
          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Já possui uma conta?{' '}
            <Link to="/login" className="text-primary font-medium hover:opacity-80 transition">
              Entre aqui
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}
