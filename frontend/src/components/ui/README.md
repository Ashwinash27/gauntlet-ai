# ArgusAI UI Components

Base UI component library for the ArgusAI dashboard using the Night Operations dark theme.

## Color Palette

### Backgrounds
- `bg-primary`: #0d1117 - Main background
- `bg-secondary`: #161b22 - Card backgrounds
- `bg-tertiary`: #21262d - Input backgrounds, hover states

### Text
- `text-primary`: #e6edf3 - Primary text
- `text-secondary`: #8b949e - Secondary text

### Semantic Colors
- `safe`: #3fb950 - Success, safe status
- `danger`: #f85149 - Error, danger, injection detected
- `warning`: #d29922 - Warning, suspicious activity
- `accent`: #58a6ff - Primary actions, links, focus states

## Components

### Button
Versatile button component with multiple variants and sizes.

```tsx
import { Button } from '@/components/ui';

<Button variant="primary" size="md" onClick={handleClick}>
  Submit
</Button>
<Button variant="danger" loading={isLoading}>
  Delete
</Button>
```

**Props:**
- `variant`: 'primary' | 'danger' | 'ghost'
- `size`: 'sm' | 'md' | 'lg'
- `loading`: boolean
- `disabled`: boolean

### Input
Text input with label and error state support.

```tsx
import { Input } from '@/components/ui';

<Input
  label="API Key"
  placeholder="Enter your API key"
  value={apiKey}
  onChange={handleChange}
  error={errorMessage}
/>
```

**Props:**
- `label`: string (optional)
- `error`: string (optional)
- `type`: string (default: 'text')

### Card
Container component for grouping content.

```tsx
import { Card } from '@/components/ui';

<Card title="Detection Stats">
  <p>Content goes here</p>
</Card>
```

**Props:**
- `title`: string (optional)
- `children`: ReactNode
- `className`: string (optional)

### Table
Complete table system with header, body, row, and cell components.

```tsx
import { Table, TableHeader, TableBody, TableRow, TableCell } from '@/components/ui';

<Table>
  <TableHeader>
    <TableRow>
      <TableCell header>Name</TableCell>
      <TableCell header>Status</TableCell>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Test</TableCell>
      <TableCell>Active</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Modal
Animated modal dialog with backdrop blur.

```tsx
import { Modal } from '@/components/ui';

<Modal isOpen={isOpen} onClose={handleClose} title="Confirm Action">
  <p>Are you sure?</p>
  <Button onClick={handleConfirm}>Yes</Button>
</Modal>
```

**Props:**
- `isOpen`: boolean
- `onClose`: () => void
- `title`: string (optional)
- `children`: ReactNode

**Features:**
- Press ESC to close
- Click backdrop to close
- Prevents body scroll when open
- Framer Motion animations

### ThemeToggle
Theme switcher button (toggles dark/light mode).

```tsx
import { ThemeToggle } from '@/components/ui';

<ThemeToggle />
```

**Features:**
- Persists to localStorage
- Sun/Moon icons from lucide-react
- Toggles 'dark' class on document.documentElement

### Spinner
Loading spinner with accent color.

```tsx
import { Spinner } from '@/components/ui';

{isLoading && <Spinner size="md" />}
```

**Props:**
- `size`: 'sm' | 'md' | 'lg'

### Badge
Status badge with semantic color variants.

```tsx
import { Badge } from '@/components/ui';

<Badge variant="success">Safe</Badge>
<Badge variant="danger">Injection Detected</Badge>
<Badge variant="warning">Suspicious</Badge>
```

**Props:**
- `variant`: 'success' | 'danger' | 'warning' | 'info' | 'neutral'
- `children`: ReactNode

## Usage

Import components from the barrel export:

```tsx
import { Button, Input, Card, Badge } from '@/components/ui';
```

Or import individually:

```tsx
import { Button } from '@/components/ui/Button';
```

## Utilities

### cn() - Class Name Merger
Utility function for merging Tailwind classes with proper conflict resolution.

```tsx
import { cn } from '@/lib/utils';

<div className={cn('bg-primary', isDanger && 'bg-danger', className)}>
```

## Demo

View all components in action by importing ComponentShowcase:

```tsx
import { ComponentShowcase } from '@/components/ui/ComponentShowcase';

<ComponentShowcase />
```

## Accessibility

All components include:
- Proper ARIA attributes
- Keyboard navigation support
- Focus visible states
- Screen reader support

## Performance

- Components use React.forwardRef where appropriate
- All components are typed with TypeScript
- No runtime style generation (Tailwind classes are static)
- Lazy loading support via React.lazy()
