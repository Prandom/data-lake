/**
 * ProtectedRoute — Redirects unauthenticated users to /login.
 *
 * While Firebase is resolving the initial auth state, shows a
 * fullscreen loading spinner so there's no flash of the login page.
 *
 * Usage:
 *   <Route element={<ProtectedRoute />}>
 *     <Route path="/" element={<ChatPage />} />
 *   </Route>
 */

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Database } from 'lucide-react'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()

  // Show branded loading state while Firebase resolves
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-surface-0 animate-fade-in">
        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-500/10 mb-5">
          <Database className="w-7 h-7 text-brand-400 animate-pulse" />
        </div>
        <div className="flex gap-1.5">
          <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
