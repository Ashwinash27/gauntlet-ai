# Layout Components - Quick Start

Get the ArgusAI dashboard layout working in 5 minutes.

## 1. Import Components

```tsx
import { Sidebar, PageLayout } from '@/components/layout'
import type { User } from '@/types'
```

## 2. Setup Router with Sidebar

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  const currentUser: User = {
    id: '1',
    email: 'admin@argusai.com',
    role: 'admin',
    name: 'Admin User'
  }

  const handleLogout = () => {
    // Your logout logic
    console.log('Logging out...')
  }

  return (
    <BrowserRouter>
      {/* Sidebar shows on all pages */}
      <Sidebar user={currentUser} onLogout={handleLogout} />

      {/* Page routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        {/* Add more routes */}
      </Routes>
    </BrowserRouter>
  )
}
```

## 3. Create Page Components

```tsx
function HomePage() {
  return (
    <PageLayout title="Overview">
      <div className="grid gap-6">
        {/* Your content */}
        <h2 className="text-text-primary">Welcome to Argus AI</h2>
      </div>
    </PageLayout>
  )
}
```

## 4. Add Breadcrumbs & Actions (Optional)

```tsx
import { Button } from '@/components/ui/Button'

function ApiKeysPage() {
  return (
    <PageLayout
      title="API Keys"
      breadcrumbs={['Settings', 'API Keys']}
      actions={
        <Button variant="primary">Create New Key</Button>
      }
    >
      <div>{/* Your content */}</div>
    </PageLayout>
  )
}
```

## Complete Minimal Example

```tsx
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar, PageLayout } from '@/components/layout'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

const user = {
  id: '1',
  email: 'user@argusai.com',
  role: 'admin' as const,
  name: 'User'
}

export default function App() {
  return (
    <BrowserRouter>
      <Sidebar user={user} onLogout={() => console.log('logout')} />

      <Routes>
        <Route path="/" element={
          <PageLayout title="Dashboard">
            <Card className="p-6">
              <h2 className="text-xl text-text-primary">Welcome!</h2>
            </Card>
          </PageLayout>
        } />

        <Route path="/analytics" element={
          <PageLayout
            title="Analytics"
            breadcrumbs={['Home', 'Analytics']}
            actions={<Button>Export</Button>}
          >
            <Card className="p-6">Analytics content</Card>
          </PageLayout>
        } />
      </Routes>
    </BrowserRouter>
  )
}
```

## Navigation Paths

The Sidebar automatically creates navigation for:

- `/` - Overview
- `/playground` - Playground
- `/analytics` - Analytics
- `/api-keys` - API Keys
- `/customers` - Customers (admin only)
- `/system` - System Health (admin only)
- `/settings` - Settings

Just create Route components for each path.

## Role-Based Access

Admin users see all navigation items. Customer users only see:
- Overview, Playground, Analytics, API Keys, Settings

The Sidebar automatically hides admin-only items based on `user.role`.

## Styling Tips

Use design system colors:
```tsx
<div className="bg-bg-secondary text-text-primary">
  <h1 className="text-accent">Highlighted text</h1>
  <p className="text-text-secondary">Secondary text</p>
</div>
```

Common patterns:
```tsx
// Card with content
<Card className="p-6">
  <h3 className="text-lg font-semibold text-text-primary mb-4">
    Section Title
  </h3>
  <p className="text-text-secondary">Description</p>
</Card>

// Grid layout
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <Card>Card 1</Card>
  <Card>Card 2</Card>
  <Card>Card 3</Card>
</div>
```

## Next Steps

- See `LayoutExample.tsx` for full working example
- Check `README.md` for detailed documentation
- View `COMPONENT_STRUCTURE.md` for visual layout guide
- Run tests: `npm test LayoutComponents.test.tsx`

## Troubleshooting

**Sidebar not showing?**
- Make sure you have `<BrowserRouter>` wrapping everything
- Sidebar should be outside `<Routes>`, not inside

**Content overlapping sidebar?**
- PageLayout automatically adds `ml-[280px]` margin
- Don't add custom margins to page content

**Navigation not highlighting?**
- Use react-router-dom's `<Route>` components
- NavLink automatically detects active routes
- Path in Route must match path in Sidebar navigation

**User not showing?**
- Pass valid User object with: id, email, role
- role must be 'admin' or 'customer'
