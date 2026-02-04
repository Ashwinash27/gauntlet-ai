import React from 'react'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface HeaderProps {
  title: string
  breadcrumbs?: string[]
  actions?: React.ReactNode
  className?: string
}

/**
 * Page header component
 * - Shows current page title
 * - Optional breadcrumbs for navigation hierarchy
 * - Slot for page-specific action buttons on the right
 * @example
 * <Header
 *   title="API Keys"
 *   breadcrumbs={['Settings', 'API Keys']}
 *   actions={<Button>Create New Key</Button>}
 * />
 */
export const Header: React.FC<HeaderProps> = ({ title, breadcrumbs, actions, className }) => {
  return (
    <header
      className={cn(
        'sticky top-0 z-10 bg-bg-primary/95 backdrop-blur-sm border-b border-bg-elevated',
        className
      )}
    >
      <div className="flex items-center justify-between px-8 py-5">
        {/* Left: Title and Breadcrumbs */}
        <div className="flex flex-col gap-1">
          {breadcrumbs && breadcrumbs.length > 0 && (
            <nav
              className="flex items-center gap-2 text-sm text-text-tertiary"
              aria-label="Breadcrumb"
            >
              {breadcrumbs.map((crumb, index) => (
                <React.Fragment key={index}>
                  {index > 0 && <ChevronRight className="w-4 h-4" />}
                  <span
                    className={cn(
                      index === breadcrumbs.length - 1
                        ? 'text-text-secondary font-medium'
                        : 'hover:text-text-secondary transition-colors'
                    )}
                  >
                    {crumb}
                  </span>
                </React.Fragment>
              ))}
            </nav>
          )}

          <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
        </div>

        {/* Right: Quick Actions */}
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </header>
  )
}
