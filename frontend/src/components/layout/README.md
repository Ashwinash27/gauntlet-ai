# Layout Components

Core layout components for the ArgusAI dashboard. Provides consistent page structure with sidebar navigation, header, and content area.

## Components

### Sidebar

Fixed left sidebar with navigation, user info, and role-based menu items.

**Props:**
- `user: User` - Current user object (required)
- `onLogout?: () => void` - Logout callback
- `className?: string` - Additional CSS classes

**Features:**
- 280px fixed width, full height
- Role-based navigation (admin vs customer)
- Active route highlighting
- User avatar and info at bottom
- Theme toggle integration
- Settings and documentation links
- Hover animations with framer-motion

**Example:**
```tsx
import { Sidebar } from '@/components/layout'

<Sidebar
  user={currentUser}
  onLogout={handleLogout}
/>
```

### Header

Page header with title, breadcrumbs, and action buttons.

**Props:**
- `title: string` - Page title (required)
- `breadcrumbs?: string[]` - Navigation breadcrumbs
- `actions?: ReactNode` - Action buttons/components
- `className?: string` - Additional CSS classes

**Features:**
- Sticky positioning at top
- Backdrop blur effect
- Breadcrumb navigation
- Right-aligned action slot

**Example:**
```tsx
import { Header } from '@/components/layout'
import { Button } from '@/components/ui/Button'

<Header
  title="API Keys"
  breadcrumbs={['Settings', 'API Keys']}
  actions={
    <>
      <Button variant="secondary">Import</Button>
      <Button variant="primary">Create New</Button>
    </>
  }
/>
```

### PageLayout

Main page wrapper that combines Header with content area.

**Props:**
- `children: ReactNode` - Page content (required)
- `title: string` - Page title (required)
- `breadcrumbs?: string[]` - Navigation breadcrumbs
- `actions?: ReactNode` - Header action buttons
- `className?: string` - Additional CSS for wrapper
- `contentClassName?: string` - Additional CSS for content area

**Features:**
- Left margin to account for sidebar (ml-[280px])
- Includes Header component
- Padding and background styling
- Full height layout

**Example:**
```tsx
import { PageLayout } from '@/components/layout'
import { Button } from '@/components/ui/Button'

<PageLayout
  title="Analytics"
  breadcrumbs={['Home', 'Analytics']}
  actions={<Button>Export Report</Button>}
>
  <div className="grid gap-6">
    {/* Your page content */}
  </div>
</PageLayout>
```

## Complete Example

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar, PageLayout } from '@/components/layout'
import { Button } from '@/components/ui/Button'

function App() {
  const currentUser = {
    id: '1',
    email: 'admin@argusai.com',
    role: 'admin',
    name: 'Admin User'
  }

  return (
    <BrowserRouter>
      {/* Fixed Sidebar - shows on all pages */}
      <Sidebar user={currentUser} onLogout={handleLogout} />

      {/* Page Routes - each uses PageLayout */}
      <Routes>
        <Route path="/" element={
          <PageLayout title="Overview">
            <div>Dashboard content here</div>
          </PageLayout>
        } />

        <Route path="/analytics" element={
          <PageLayout
            title="Analytics"
            breadcrumbs={['Home', 'Analytics']}
            actions={<Button>Export</Button>}
          >
            <div>Analytics content here</div>
          </PageLayout>
        } />
      </Routes>
    </BrowserRouter>
  )
}
```

## Navigation Items

The Sidebar includes these navigation items:

**All Users:**
- Overview (LayoutDashboard icon)
- Playground (FlaskConical icon)
- Analytics (BarChart3 icon)
- API Keys (Key icon)

**Admin Only:**
- Customers (Users icon)
- System Health (Activity icon)

**Always Visible:**
- Settings (Settings icon)
- Documentation (ExternalLink icon) - opens in new tab

## Styling

Uses design system colors from tailwind.config.js:
- `bg-primary`: #0d1117 (main background)
- `bg-secondary`: #161b22 (sidebar background)
- `bg-tertiary`: #21262d (hover states)
- `bg-elevated`: #30363d (borders, dividers)
- `text-primary`: #e6edf3 (main text)
- `text-secondary`: #8b949e (secondary text)
- `text-tertiary`: #6e7681 (muted text)
- `accent`: #58a6ff (active states, highlights)

## Responsive Design

Currently optimized for desktop (1024px+). The layout:
- Sidebar: Fixed 280px width on left
- Content: Left margin of 280px to prevent overlap
- Mobile responsiveness coming in future update

## Accessibility

- Semantic HTML (nav, header, main)
- ARIA labels for navigation and breadcrumbs
- Keyboard navigation support (focus-visible rings)
- Screen reader friendly navigation structure
- Proper heading hierarchy (h1 for page titles)

## Performance

- Uses framer-motion for smooth animations
- NavLink for automatic active state management
- Minimal re-renders (props are memoized where appropriate)
- Lazy loading ready (components can be code-split)

## Testing

See `__tests__/LayoutComponents.test.tsx` for comprehensive test coverage:
- Role-based navigation visibility
- User information display
- Breadcrumb rendering
- Action button integration
- Accessibility compliance
