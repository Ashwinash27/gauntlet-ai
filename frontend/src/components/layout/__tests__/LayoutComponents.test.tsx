import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Sidebar, Header, PageLayout } from '../index'
import type { User } from '@/types'

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
}))

const mockAdminUser: User = {
  id: '1',
  email: 'admin@test.com',
  role: 'admin',
  name: 'Admin User',
}

const mockCustomerUser: User = {
  id: '2',
  email: 'customer@test.com',
  role: 'customer',
  name: 'Customer User',
}

describe('Sidebar', () => {
  it('renders logo and branding', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
      </BrowserRouter>
    )
    expect(screen.getByText('Argus AI')).toBeInTheDocument()
  })

  it('displays user role badge', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
      </BrowserRouter>
    )
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('shows all navigation items for admin', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
      </BrowserRouter>
    )
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Playground')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('API Keys')).toBeInTheDocument()
    expect(screen.getByText('Customers')).toBeInTheDocument()
    expect(screen.getByText('System Health')).toBeInTheDocument()
  })

  it('hides admin-only items for customer users', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockCustomerUser} />
      </BrowserRouter>
    )
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.queryByText('Customers')).not.toBeInTheDocument()
    expect(screen.queryByText('System Health')).not.toBeInTheDocument()
  })

  it('displays user information', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
      </BrowserRouter>
    )
    expect(screen.getByText('Admin User')).toBeInTheDocument()
    expect(screen.getByText('admin@test.com')).toBeInTheDocument()
  })

  it('shows logout button when onLogout provided', () => {
    const handleLogout = vi.fn()
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} onLogout={handleLogout} />
      </BrowserRouter>
    )
    expect(screen.getByText('Logout')).toBeInTheDocument()
  })

  it('shows settings and documentation links', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
      </BrowserRouter>
    )
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Documentation')).toBeInTheDocument()
  })
})

describe('Header', () => {
  it('renders title', () => {
    render(<Header title="Test Page" />)
    expect(screen.getByText('Test Page')).toBeInTheDocument()
  })

  it('renders breadcrumbs when provided', () => {
    render(<Header title="Test Page" breadcrumbs={['Home', 'Settings', 'Test Page']} />)
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders action buttons when provided', () => {
    render(
      <Header
        title="Test Page"
        actions={<button>Test Action</button>}
      />
    )
    expect(screen.getByText('Test Action')).toBeInTheDocument()
  })

  it('works without breadcrumbs and actions', () => {
    render(<Header title="Simple Page" />)
    expect(screen.getByText('Simple Page')).toBeInTheDocument()
  })
})

describe('PageLayout', () => {
  it('renders title in header', () => {
    render(
      <PageLayout title="Test Page">
        <div>Content</div>
      </PageLayout>
    )
    expect(screen.getByText('Test Page')).toBeInTheDocument()
  })

  it('renders children content', () => {
    render(
      <PageLayout title="Test Page">
        <div>Page Content Here</div>
      </PageLayout>
    )
    expect(screen.getByText('Page Content Here')).toBeInTheDocument()
  })

  it('passes breadcrumbs to header', () => {
    render(
      <PageLayout title="Test Page" breadcrumbs={['Home', 'Test']}>
        <div>Content</div>
      </PageLayout>
    )
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Test')).toBeInTheDocument()
  })

  it('passes actions to header', () => {
    render(
      <PageLayout title="Test Page" actions={<button>Action Button</button>}>
        <div>Content</div>
      </PageLayout>
    )
    expect(screen.getByText('Action Button')).toBeInTheDocument()
  })
})

describe('Layout Integration', () => {
  it('combines sidebar and page layout correctly', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
        <PageLayout title="Dashboard">
          <div>Dashboard Content</div>
        </PageLayout>
      </BrowserRouter>
    )
    expect(screen.getByText('Argus AI')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
  })
})

describe('Accessibility', () => {
  it('sidebar has proper ARIA labels', () => {
    render(
      <BrowserRouter>
        <Sidebar user={mockAdminUser} />
      </BrowserRouter>
    )
    const nav = screen.getByRole('navigation')
    expect(nav).toBeInTheDocument()
  })

  it('header uses proper heading hierarchy', () => {
    render(<Header title="Test Page" />)
    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toHaveTextContent('Test Page')
  })

  it('breadcrumbs have proper ARIA label', () => {
    render(<Header title="Test" breadcrumbs={['Home', 'Test']} />)
    const breadcrumb = screen.getByLabelText('Breadcrumb')
    expect(breadcrumb).toBeInTheDocument()
  })
})
