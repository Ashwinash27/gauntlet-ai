import React, { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar, PageLayout } from './index'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import type { User } from '@/types'

/**
 * Example usage of layout components
 * Shows how to structure a complete dashboard page with Sidebar + PageLayout
 */

// Mock user data
const mockAdminUser: User = {
  id: '1',
  email: 'admin@argusai.com',
  role: 'admin',
  name: 'Admin User',
}

const mockCustomerUser: User = {
  id: '2',
  email: 'customer@example.com',
  role: 'customer',
  name: 'John Doe',
}

// Example page components
const OverviewPage: React.FC = () => (
  <PageLayout title="Overview" actions={<Button variant="primary">Refresh</Button>}>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-2">Total Requests</h3>
        <p className="text-3xl font-bold text-accent">1,234</p>
      </Card>
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-2">Detections</h3>
        <p className="text-3xl font-bold text-danger">42</p>
      </Card>
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-2">Avg Latency</h3>
        <p className="text-3xl font-bold text-safe">125ms</p>
      </Card>
    </div>
  </PageLayout>
)

const PlaygroundPage: React.FC = () => (
  <PageLayout
    title="Playground"
    breadcrumbs={['Home', 'Playground']}
    actions={
      <div className="flex gap-2">
        <Button variant="ghost">Load Example</Button>
        <Button variant="primary">Test Prompt</Button>
      </div>
    }
  >
    <Card className="p-6">
      <p className="text-text-secondary">
        Test your prompts for injection vulnerabilities in real-time.
      </p>
    </Card>
  </PageLayout>
)

const AnalyticsPage: React.FC = () => (
  <PageLayout
    title="Analytics"
    breadcrumbs={['Home', 'Analytics']}
    actions={<Button variant="ghost">Export Report</Button>}
  >
    <Card className="p-6">
      <p className="text-text-secondary">View detailed analytics and insights.</p>
    </Card>
  </PageLayout>
)

const ApiKeysPage: React.FC = () => (
  <PageLayout
    title="API Keys"
    breadcrumbs={['Settings', 'API Keys']}
    actions={<Button variant="primary">Create New Key</Button>}
  >
    <Card className="p-6">
      <p className="text-text-secondary">Manage your API keys and access tokens.</p>
    </Card>
  </PageLayout>
)

const CustomersPage: React.FC = () => (
  <PageLayout
    title="Customers"
    breadcrumbs={['Admin', 'Customers']}
    actions={<Button variant="primary">Add Customer</Button>}
  >
    <Card className="p-6">
      <p className="text-text-secondary">Manage customer accounts (Admin only).</p>
    </Card>
  </PageLayout>
)

const SystemHealthPage: React.FC = () => (
  <PageLayout
    title="System Health"
    breadcrumbs={['Admin', 'System Health']}
    actions={<Button variant="ghost">Run Diagnostics</Button>}
  >
    <Card className="p-6">
      <p className="text-text-secondary">Monitor system performance and health metrics.</p>
    </Card>
  </PageLayout>
)

const SettingsPage: React.FC = () => (
  <PageLayout title="Settings" breadcrumbs={['Settings']}>
    <Card className="p-6">
      <p className="text-text-secondary">Configure your account settings.</p>
    </Card>
  </PageLayout>
)

/**
 * Full dashboard example with sidebar and routing
 * Toggle between admin and customer views to see role-based navigation
 */
export const LayoutExample: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User>(mockAdminUser)

  const handleLogout = () => {
    console.log('Logout clicked')
    // In real app: clear session, redirect to login
  }

  const toggleUserRole = () => {
    setCurrentUser((prev) =>
      prev.role === 'admin' ? mockCustomerUser : mockAdminUser
    )
  }

  return (
    <BrowserRouter>
      {/* Fixed Sidebar */}
      <Sidebar user={currentUser} onLogout={handleLogout} />

      {/* Page Content with left margin for sidebar */}
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/system" element={<SystemHealthPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>

      {/* Dev Helper: Toggle user role */}
      <div className="fixed bottom-4 right-4 z-50">
        <Button onClick={toggleUserRole} variant="ghost" className="shadow-lg">
          Switch to {currentUser.role === 'admin' ? 'Customer' : 'Admin'}
        </Button>
      </div>
    </BrowserRouter>
  )
}
