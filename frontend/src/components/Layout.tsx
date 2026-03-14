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
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-lg font-bold text-blue-600">
              Article Summarizer
            </Link>
            <Link to="/historico" className="text-sm text-gray-600 hover:text-gray-900">
              History
            </Link>
            {isAuthenticated && (
              <Link to="/configuracoes" className="text-sm text-gray-600 hover:text-gray-900">
                Settings
              </Link>
            )}
          </div>
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-gray-500">{username}</span>
                <button
                  onClick={handleLogout}
                  className="text-sm text-red-600 hover:text-red-700"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link to="/login" className="text-sm text-blue-600 hover:text-blue-700">
                Login
              </Link>
            )}
          </div>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Outlet />
      </main>
      <footer className="text-center py-4 text-xs text-gray-400 border-t mt-8">
        Article Summarizer Agent — Clean Architecture Flask + React
      </footer>
    </div>
  )
}
