import { useQuery } from '@tanstack/react-query'
import { getSettings, clearCache, rotateSecret } from '../api/settings'
import { useAuth } from '../hooks/useAuth'
import { useState } from 'react'

export default function SettingsPage() {
  const { isAuthenticated, role } = useAuth()
  const [message, setMessage] = useState<string | null>(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
    enabled: isAuthenticated,
  })

  if (!isAuthenticated) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Settings</h1>
        <p className="text-gray-500">Please log in to access settings.</p>
      </div>
    )
  }

  const handleClearCache = async () => {
    try {
      await clearCache()
      setMessage('Cache cleared successfully.')
    } catch {
      setMessage('Failed to clear cache.')
    }
  }

  const handleRotateSecret = async () => {
    if (
      !confirm(
        'Are you sure you want to rotate the JWT secret? All sessions will be invalidated after the grace period.'
      )
    )
      return
    try {
      await rotateSecret()
      setMessage('JWT secret rotated successfully.')
    } catch {
      setMessage('Failed to rotate secret.')
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {message && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded p-3">
          {message}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-500">Loading settings...</p>
      ) : (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold mb-4">Current Configuration</h2>
          <dl className="space-y-2">
            {settings &&
              Object.entries(settings).map(([key, value]) => (
                <div key={key} className="grid grid-cols-2 gap-2 text-sm">
                  <dt className="font-mono text-gray-500">{key}</dt>
                  <dd className="text-gray-800">{JSON.stringify(value)}</dd>
                </div>
              ))}
          </dl>
        </div>
      )}

      {role === 'admin' && (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold mb-4">Admin Actions</h2>
          <div className="flex gap-3">
            <button
              onClick={handleClearCache}
              className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
            >
              Clear Cache
            </button>
            <button
              onClick={handleRotateSecret}
              className="px-4 py-2 text-sm bg-red-100 hover:bg-red-200 text-red-700 rounded-md"
            >
              Rotate JWT Secret
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
