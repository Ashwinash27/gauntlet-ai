# Pages Documentation

This directory contains all page components for the ArgusAI dashboard.

## Available Pages

### APIKeys.tsx
**Route:** `/api-keys`

Manage API keys for authentication with the ArgusAI detection API.

**Features:**
- View all API keys in a table with masked key display
- Create new API keys with custom rate limits
- Revoke existing keys (with confirmation)
- Copy full key to clipboard (shown only once during creation)
- Admin users see all keys, customers see only their own

**Components Used:**
- `PageLayout` - Main layout wrapper
- `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableCell` - API keys table
- `Modal` - Create key, success, and revoke confirmation modals
- `Button`, `Input`, `Badge`, `Card`, `Spinner` - UI components

**State Management:**
- `useApiKeys` hook - Fetch, create, and revoke API keys
- `useAuth` hook - Check admin status

**Security:**
- API keys are masked as `sk-argus-...xyz` (prefix + last 4 chars)
- Full key is only shown once in success modal after creation
- Revocation requires confirmation to prevent accidental deletion

**Usage Example:**
```tsx
import { APIKeys } from '@/pages'

// In router configuration
<Route path="/api-keys" element={<APIKeys />} />
```

---

### Settings.tsx
**Route:** `/settings`

User account settings and preferences.

**Features:**
- **Account Section:**
  - Update display name
  - View email (read-only)
  - Change password (via modal)

- **Preferences Section:**
  - Theme toggle (dark/light mode)
  - Notification preferences (future - currently disabled)

- **Danger Zone:**
  - Delete account (shows warning modal, currently disabled)

**Components Used:**
- `PageLayout` - Main layout wrapper
- `Card` - Section containers
- `Input` - Form inputs
- `Button` - Action buttons
- `Modal` - Password change and account deletion modals
- `ThemeToggle` - Theme switcher

**State Management:**
- `useAuth` hook - Get current user data
- Supabase client - Update user metadata and password

**Form Validation:**
- Display name cannot be empty
- Password must be at least 8 characters
- Password confirmation must match
- All fields required for password change

**Usage Example:**
```tsx
import { Settings } from '@/pages'

// In router configuration
<Route path="/settings" element={<Settings />} />
```

---

## Common Patterns

### Page Layout Structure
All pages use the `PageLayout` component which provides:
- Fixed sidebar offset (280px left margin)
- Header with title, breadcrumbs, and actions
- Content area with padding and background

```tsx
<PageLayout
  title="Page Title"
  actions={<Button>Action</Button>}
>
  <div className="max-w-4xl">
    {/* Page content */}
  </div>
</PageLayout>
```

### Modal Pattern
Modals are used for:
- Create/edit operations
- Confirmation dialogs
- Success messages with important info

```tsx
const [showModal, setShowModal] = useState(false)

<Modal
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  title="Modal Title"
>
  {/* Modal content */}
</Modal>
```

### Error Handling
Display errors using styled alert boxes:

```tsx
{error && (
  <div className="p-4 rounded-md bg-[#f85149]/10 border border-[#f85149]/30">
    <div className="flex items-start">
      <AlertTriangle className="w-5 h-5 text-[#f85149] mr-3 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-[#f85149]">Error Title</p>
        <p className="text-sm text-[#f85149]/80 mt-1">{error}</p>
      </div>
    </div>
  </div>
)}
```

### Loading States
Use the `Spinner` component for loading states:

```tsx
{loading ? (
  <div className="flex items-center justify-center py-12">
    <Spinner size="lg" />
  </div>
) : (
  // Content
)}
```

### Empty States
Provide helpful empty states when no data exists:

```tsx
<div className="text-center py-12">
  <div className="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-[#21262d] border border-[#30363d]">
    <Icon className="w-8 h-8 text-[#8b949e]" />
  </div>
  <h3 className="text-lg font-medium text-[#e6edf3] mb-2">No data yet</h3>
  <p className="text-[#8b949e] mb-6">Description of what to do</p>
  <Button onClick={action}>Call to Action</Button>
</div>
```

## Accessibility Checklist

### APIKeys Page
- [x] Table headers use semantic `<th>` elements
- [x] Buttons have descriptive text and icons
- [x] Modals close on Escape key
- [x] Modals trap focus
- [x] Status badges use color + text (not just color)
- [x] Copy button provides visual feedback
- [x] Loading states announced via spinner aria-label

### Settings Page
- [x] Form inputs have labels
- [x] Password inputs use type="password"
- [x] Disabled inputs are clearly marked
- [x] Form validation shows error messages
- [x] Success feedback is visible
- [x] Modal confirmations prevent accidental actions
- [x] Theme toggle has aria-label

## Performance Considerations

### APIKeys
- API keys list is fetched once on mount
- Optimistic UI updates on revoke (local state updated before API call)
- Debounced input validation for create modal
- Table rows are not virtualized (assume < 100 keys per user)

### Settings
- User data loaded from `useAuth` hook (already cached)
- Theme preference stored in localStorage (instant read)
- Password change only updates when form is submitted
- No unnecessary re-renders (form state is local)

## Future Enhancements

### APIKeys
- [ ] Edit rate limit in-place
- [ ] Usage statistics per API key
- [ ] API key expiration dates
- [ ] Usage alerts when approaching rate limit
- [ ] Bulk revoke multiple keys

### Settings
- [ ] Email change functionality
- [ ] Two-factor authentication
- [ ] Email notification preferences
- [ ] Detection alert configuration
- [ ] Export user data
- [ ] API usage export

## Testing

Basic test structure for pages:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { APIKeys } from './APIKeys'

// Mock hooks
vi.mock('@/hooks/useApiKeys', () => ({
  useApiKeys: () => ({
    keys: [],
    loading: false,
    error: null,
    createKey: vi.fn(),
    revokeKey: vi.fn(),
    refresh: vi.fn(),
  }),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@test.com', role: 'customer' },
    loading: false,
    error: null,
    isAdmin: false,
  }),
}))

describe('APIKeys', () => {
  it('renders page title', () => {
    render(
      <BrowserRouter>
        <APIKeys />
      </BrowserRouter>
    )
    expect(screen.getByText('API Keys')).toBeInTheDocument()
  })

  it('shows create button', () => {
    render(
      <BrowserRouter>
        <APIKeys />
      </BrowserRouter>
    )
    expect(screen.getByText('Create New Key')).toBeInTheDocument()
  })
})
```

Run tests:
```bash
npm test APIKeys
npm test Settings
```
