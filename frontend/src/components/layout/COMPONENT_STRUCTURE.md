# Layout Component Structure

Visual guide to the ArgusAI dashboard layout architecture.

## Component Hierarchy

```
App (BrowserRouter)
├── Sidebar (fixed, left side, 280px)
│   ├── Logo & Branding
│   │   ├── Shield Icon
│   │   ├── "Argus AI" Title
│   │   └── Role Badge (Admin/Customer)
│   │
│   ├── Navigation Menu
│   │   ├── Overview
│   │   ├── Playground
│   │   ├── Analytics
│   │   ├── API Keys
│   │   ├── ─── Admin Divider ───
│   │   ├── Customers (admin only)
│   │   └── System Health (admin only)
│   │
│   └── Bottom Section
│       ├── Settings Link
│       ├── Documentation Link (external)
│       ├── Theme Toggle
│       ├── User Info (avatar, name, email)
│       └── Logout Button
│
└── PageLayout (main content, ml-[280px])
    ├── Header (sticky top)
    │   ├── Left: Title + Breadcrumbs
    │   └── Right: Action Buttons
    │
    └── Main Content Area (p-8)
        └── {children}
```

## Layout Dimensions

```
┌─────────────────────────────────────────────────────┐
│  Sidebar (280px fixed)  │  Main Content             │
│  ─────────────────────  │  ─────────────            │
│  [Logo]                 │  Header (sticky)          │
│  Argus AI              │  ┌─────────────────────┐  │
│  [Admin Badge]         │  │ Title    [Actions]  │  │
│                        │  │ Breadcrumbs         │  │
│  Navigation:           │  └─────────────────────┘  │
│  ▸ Overview            │                           │
│  □ Playground          │  Content Area (p-8)       │
│  □ Analytics           │  ┌─────────────────────┐  │
│  □ API Keys            │  │                     │  │
│  ───────────           │  │  Your page content  │  │
│  Admin:                │  │  goes here          │  │
│  □ Customers           │  │                     │  │
│  □ System Health       │  └─────────────────────┘  │
│                        │                           │
│  [Settings]            │                           │
│  [Docs 🔗]             │                           │
│  [Theme Toggle]        │                           │
│                        │                           │
│  ┌───────────────────┐ │                           │
│  │ [A] Admin User    │ │                           │
│  │ admin@argus.com   │ │                           │
│  └───────────────────┘ │                           │
│  [Logout]              │                           │
└─────────────────────────────────────────────────────┘
```

## Color Mapping

```
Sidebar:
├── Background: bg-secondary (#161b22)
├── Borders: bg-elevated (#30363d)
├── Hover: bg-tertiary (#21262d)
└── Active: accent/10 with accent text (#58a6ff)

Header:
├── Background: bg-primary/95 with backdrop-blur
└── Border: bg-elevated (#30363d)

Content Area:
└── Background: bg-primary (#0d1117)
```

## State Variants

### Navigation Item States

**Default:**
```css
text-text-secondary hover:text-text-primary
hover:bg-bg-tertiary
```

**Active:**
```css
bg-accent/10 text-accent
hover:bg-accent/15
```

**Focus:**
```css
focus-visible:ring-2 focus-visible:ring-accent
```

## Props Flow

```typescript
// App Level
<BrowserRouter>
  <Sidebar
    user={currentUser}           // User object with role
    onLogout={handleLogout}      // Optional logout handler
  />

  <Routes>
    <Route path="/" element={
      <PageLayout
        title="Overview"          // Page title (required)
        breadcrumbs={['Home']}   // Optional breadcrumbs
        actions={<Button />}      // Optional action buttons
      >
        {/* Page content here */}
      </PageLayout>
    } />
  </Routes>
</BrowserRouter>
```

## Animation Details

Uses framer-motion for subtle interactions:

**Sidebar Navigation Items:**
- `whileHover={{ x: 2 }}` - Slight right shift on hover
- `transition={{ duration: 0.2 }}` - Smooth 200ms transition

**Logout Button:**
- Same hover animation as nav items
- Color changes to danger theme on hover

## Responsive Breakpoints

Current implementation:
- Desktop: 1024px+ (full layout as designed)

Future considerations:
- Tablet (768px-1023px): Collapsible sidebar
- Mobile (<768px): Bottom navigation or hamburger menu

## Usage Patterns

### Simple Page
```tsx
<PageLayout title="Dashboard">
  <Card>Content</Card>
</PageLayout>
```

### Page with Breadcrumbs
```tsx
<PageLayout
  title="API Keys"
  breadcrumbs={['Settings', 'API Keys']}
>
  <Card>Content</Card>
</PageLayout>
```

### Page with Actions
```tsx
<PageLayout
  title="Analytics"
  actions={
    <>
      <Button variant="secondary">Export</Button>
      <Button variant="primary">Refresh</Button>
    </>
  }
>
  <Card>Content</Card>
</PageLayout>
```

### Full Example
```tsx
<PageLayout
  title="System Health"
  breadcrumbs={['Admin', 'System Health']}
  actions={
    <Button variant="secondary">Run Diagnostics</Button>
  }
>
  <div className="grid gap-6">
    <Card>Metrics</Card>
    <Card>Alerts</Card>
  </div>
</PageLayout>
```

## File Locations

```
/mnt/d/Projects/ArgusAI/frontend/src/components/layout/
├── Sidebar.tsx           # 280px fixed navigation
├── Header.tsx            # Sticky page header
├── PageLayout.tsx        # Main content wrapper
├── index.ts             # Public exports
├── LayoutExample.tsx    # Usage examples
├── README.md            # Documentation
├── COMPONENT_STRUCTURE.md  # This file
└── __tests__/
    └── LayoutComponents.test.tsx  # Test suite
```
