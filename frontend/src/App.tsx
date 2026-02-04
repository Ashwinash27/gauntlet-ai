import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Sidebar } from '@/components/layout'
import {
  Login,
  Overview,
  Playground,
  History,
  APIKeys,
  Docs,
  NotFound,
} from '@/pages'

/**
 * Full page loading spinner
 * Shown during initial auth check
 */
function LoadingScreen() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
      <div className="text-center">
        <p className="text-[#00ff00] text-sm animate-pulse">&gt; Initializing...</p>
      </div>
    </div>
  )
}

/**
 * Protected route wrapper
 * Redirects to login if not authenticated
 */
interface ProtectedRouteProps {
  children: React.ReactNode
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading, signOut } = useAuth()

  if (loading) {
    return <LoadingScreen />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex min-h-screen bg-[#0a0a0a]">
      <Sidebar user={user} onLogout={signOut} />
      <main className="flex-1">{children}</main>
    </div>
  )
}

/**
 * Main App component with routing
 *
 * Routes:
 * - /login - Public login page
 * - / - Redirects to /overview
 * - /overview - Dashboard overview (protected)
 * - /playground - Test detection (protected)
 * - /history - Request logs (protected)
 * - /api-keys - API key management (protected)
 * - * - 404 not found
 */
export default function App() {
  const { user, loading } = useAuth()

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          loading ? (
            <LoadingScreen />
          ) : user ? (
            <Navigate to="/overview" replace />
          ) : (
            <Login />
          )
        }
      />

      {/* Root redirect */}
      <Route path="/" element={<Navigate to="/overview" replace />} />

      {/* Protected routes */}
      <Route
        path="/overview"
        element={
          <ProtectedRoute>
            <Overview />
          </ProtectedRoute>
        }
      />
      <Route
        path="/playground"
        element={
          <ProtectedRoute>
            <Playground />
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <History />
          </ProtectedRoute>
        }
      />
      <Route
        path="/api-keys"
        element={
          <ProtectedRoute>
            <APIKeys />
          </ProtectedRoute>
        }
      />
      <Route
        path="/docs"
        element={
          <ProtectedRoute>
            <Docs />
          </ProtectedRoute>
        }
      />

      {/* 404 catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
