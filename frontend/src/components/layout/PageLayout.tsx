import React from 'react'
import { cn } from '@/lib/utils'
import { Header } from './Header'

export interface PageLayoutProps {
  children: React.ReactNode
  title: string
  breadcrumbs?: string[]
  actions?: React.ReactNode
  className?: string
  contentClassName?: string
}

/**
 * Main page layout wrapper
 * - Accounts for fixed sidebar with left margin (ml-[280px])
 * - Includes Header component at top
 * - Content area with padding and bg-primary background
 * - Responsive: Handles sidebar offset automatically
 * @example
 * <PageLayout
 *   title="Analytics"
 *   actions={<Button>Export Report</Button>}
 * >
 *   <YourPageContent />
 * </PageLayout>
 */
export const PageLayout: React.FC<PageLayoutProps> = ({
  children,
  title,
  breadcrumbs,
  actions,
  className,
  contentClassName,
}) => {
  return (
    <div className={cn('ml-[280px] min-h-screen bg-bg-primary', className)}>
      {/* Page Header */}
      <Header title={title} breadcrumbs={breadcrumbs} actions={actions} />

      {/* Main Content Area */}
      <main className={cn('p-8', contentClassName)}>{children}</main>
    </div>
  )
}
