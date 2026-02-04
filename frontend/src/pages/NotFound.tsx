import { Link } from 'react-router-dom'

/**
 * 404 Not Found page - Terminal style
 */
export function NotFound() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center px-4">
      <div className="terminal-box rounded-lg p-8 max-w-md text-center">
        <p className="text-[#ff0000] text-6xl font-bold mb-4">404</p>

        <p className="text-[#00ff00] text-sm mb-2">&gt; ERROR: Page not found</p>
        <p className="text-[#006600] text-xs mb-6">
          &gt; The requested resource does not exist
        </p>

        <Link
          to="/overview"
          className="inline-block px-6 py-2 text-sm border border-[#00ff00] text-[#00ff00] bg-[#003300] hover:bg-[#004400] transition-colors"
        >
          [RETURN TO DASHBOARD]
        </Link>
      </div>
    </div>
  )
}
