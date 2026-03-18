import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { logout } from '../api/auth'

export default function Layout() {
  const { isAuthenticated, username } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      navigate('/login')
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background-light dark:bg-background-dark">
      {/* Sticky header */}
      <header className="flex items-center justify-between whitespace-nowrap border-b border-slate-200 dark:border-slate-800 px-6 py-3 bg-background-light dark:bg-background-dark sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="size-8 bg-primary rounded-lg flex items-center justify-center text-white shrink-0">
              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
            </div>
            <h2 className="text-slate-900 dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">
              Sumarizador.ai
            </h2>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="flex items-center justify-center rounded-lg h-10 px-4 bg-primary text-white text-sm font-bold transition hover:opacity-90"
          >
            <span className="material-symbols-outlined text-[18px] mr-1.5">add</span>
            Novo Resumo
          </Link>

          <Link
            to="/historico"
            className="flex items-center justify-center rounded-lg h-10 w-10 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-white transition hover:bg-primary/20"
            aria-label="Histórico"
          >
            <span className="material-symbols-outlined text-[20px]">history</span>
          </Link>

          {isAuthenticated ? (
            <>
              {username && (
                <span className="hidden sm:block text-sm text-slate-500 dark:text-slate-400 max-w-[120px] truncate">
                  {username}
                </span>
              )}
              <Link
                to="/configuracoes"
                className="flex items-center justify-center rounded-lg h-10 w-10 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-white transition hover:bg-primary/20"
                aria-label="Configurações"
              >
                <span className="material-symbols-outlined text-[20px]">settings</span>
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 rounded-lg h-10 px-3 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-white text-sm font-medium transition hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 dark:hover:text-red-400"
                aria-label="Sair da conta"
              >
                <span className="material-symbols-outlined text-[18px]">logout</span>
                <span className="hidden sm:block">Sair</span>
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center justify-center rounded-lg h-10 px-4 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Entrar
            </Link>
          )}
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 py-5 px-6">
        <p className="text-center text-xs text-slate-400 dark:text-slate-600">
          &copy; {new Date().getFullYear()} Sumarizador.ai — Powered by Clean Architecture Flask + React
        </p>
      </footer>
    </div>
  )
}
