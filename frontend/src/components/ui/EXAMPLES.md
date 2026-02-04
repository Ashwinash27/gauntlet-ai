# Component Usage Examples

## Button

### Basic Usage
```tsx
import { Button } from '@/components/ui';

// Primary button (default)
<Button onClick={handleSubmit}>Submit</Button>

// Different variants
<Button variant="danger" onClick={handleDelete}>Delete</Button>
<Button variant="ghost" onClick={handleCancel}>Cancel</Button>

// Different sizes
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>

// Loading state
<Button loading={isSubmitting}>Saving...</Button>

// Disabled state
<Button disabled>Not Available</Button>
```

### Form Buttons
```tsx
<form onSubmit={handleSubmit}>
  <Button type="submit" variant="primary">
    Create API Key
  </Button>
  <Button type="button" variant="ghost" onClick={handleCancel}>
    Cancel
  </Button>
</form>
```

### Icon Buttons
```tsx
import { Trash2, Plus } from 'lucide-react';

<Button variant="danger" size="sm">
  <Trash2 className="h-4 w-4 mr-2" />
  Delete
</Button>

<Button variant="primary">
  <Plus className="h-4 w-4 mr-2" />
  Add New
</Button>
```

## Input

### Basic Input
```tsx
import { Input } from '@/components/ui';
import { useState } from 'react';

const [apiKey, setApiKey] = useState('');

<Input
  label="API Key"
  placeholder="Enter your API key"
  value={apiKey}
  onChange={(e) => setApiKey(e.target.value)}
/>
```

### Input with Error
```tsx
const [email, setEmail] = useState('');
const [error, setError] = useState('');

const validateEmail = (value: string) => {
  if (!value.includes('@')) {
    setError('Invalid email format');
  } else {
    setError('');
  }
};

<Input
  label="Email"
  type="email"
  value={email}
  onChange={(e) => {
    setEmail(e.target.value);
    validateEmail(e.target.value);
  }}
  error={error}
/>
```

### Different Input Types
```tsx
<Input type="password" label="Password" />
<Input type="email" label="Email" />
<Input type="number" label="Port" placeholder="8080" />
<Input type="url" label="Webhook URL" />
```

## Card

### Simple Card
```tsx
import { Card } from '@/components/ui';

<Card>
  <p>Card content without a title</p>
</Card>
```

### Card with Title
```tsx
<Card title="Detection Statistics">
  <div className="space-y-4">
    <div>Total Requests: 1,234</div>
    <div>Blocked: 56</div>
    <div>Success Rate: 95.4%</div>
  </div>
</Card>
```

### Nested Cards
```tsx
<Card title="Dashboard" className="max-w-4xl">
  <div className="grid grid-cols-2 gap-4">
    <Card title="Layer 1">
      <p>Rules-based detection</p>
    </Card>
    <Card title="Layer 2">
      <p>Embedding similarity</p>
    </Card>
  </div>
</Card>
```

## Table

### Complete Table Example
```tsx
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableCell,
  Badge
} from '@/components/ui';

const logs = [
  { id: 1, timestamp: '2026-02-03 14:32:01', status: 'safe', layer: 1 },
  { id: 2, timestamp: '2026-02-03 14:31:45', status: 'blocked', layer: 2 },
];

<Table>
  <TableHeader>
    <TableRow>
      <TableCell header>Timestamp</TableCell>
      <TableCell header>Status</TableCell>
      <TableCell header>Layer</TableCell>
    </TableRow>
  </TableHeader>
  <TableBody>
    {logs.map((log) => (
      <TableRow key={log.id}>
        <TableCell>{log.timestamp}</TableCell>
        <TableCell>
          <Badge variant={log.status === 'safe' ? 'success' : 'danger'}>
            {log.status}
          </Badge>
        </TableCell>
        <TableCell>Layer {log.layer}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### Clickable Table Rows
```tsx
<TableBody>
  {items.map((item) => (
    <TableRow
      key={item.id}
      onClick={() => handleRowClick(item.id)}
    >
      <TableCell>{item.name}</TableCell>
      <TableCell>{item.value}</TableCell>
    </TableRow>
  ))}
</TableBody>
```

### Empty State
```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableCell header>Name</TableCell>
      <TableCell header>Status</TableCell>
    </TableRow>
  </TableHeader>
  <TableBody>
    {data.length === 0 ? (
      <TableRow>
        <TableCell colSpan={2} className="text-center text-text-secondary">
          No data available
        </TableCell>
      </TableRow>
    ) : (
      data.map((row) => (
        <TableRow key={row.id}>
          <TableCell>{row.name}</TableCell>
          <TableCell>{row.status}</TableCell>
        </TableRow>
      ))
    )}
  </TableBody>
</Table>
```

## Modal

### Confirmation Modal
```tsx
import { Modal, Button } from '@/components/ui';
import { useState } from 'react';

const [isOpen, setIsOpen] = useState(false);

<>
  <Button onClick={() => setIsOpen(true)}>
    Delete Item
  </Button>

  <Modal
    isOpen={isOpen}
    onClose={() => setIsOpen(false)}
    title="Confirm Deletion"
  >
    <div className="space-y-4">
      <p className="text-text-primary">
        Are you sure you want to delete this item? This action cannot be undone.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={() => setIsOpen(false)}>
          Cancel
        </Button>
        <Button variant="danger" onClick={handleDelete}>
          Delete
        </Button>
      </div>
    </div>
  </Modal>
</>
```

### Form Modal
```tsx
const [isOpen, setIsOpen] = useState(false);
const [formData, setFormData] = useState({ name: '', email: '' });

<Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Create User">
  <form onSubmit={handleSubmit} className="space-y-4">
    <Input
      label="Name"
      value={formData.name}
      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
    />
    <Input
      label="Email"
      type="email"
      value={formData.email}
      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
    />
    <div className="flex justify-end gap-3">
      <Button type="button" variant="ghost" onClick={() => setIsOpen(false)}>
        Cancel
      </Button>
      <Button type="submit" variant="primary">
        Create
      </Button>
    </div>
  </form>
</Modal>
```

### Modal without Title
```tsx
<Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
  <div className="text-center py-4">
    <h2 className="text-xl font-semibold mb-4">Custom Header</h2>
    <p>Modal content goes here</p>
  </div>
</Modal>
```

## Badge

### Status Badges
```tsx
import { Badge } from '@/components/ui';

<Badge variant="success">Active</Badge>
<Badge variant="danger">Error</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="info">Processing</Badge>
<Badge variant="neutral">Unknown</Badge>
```

### Badge with Icons
```tsx
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';

<Badge variant="success">
  <CheckCircle className="h-3 w-3 mr-1" />
  Safe
</Badge>

<Badge variant="danger">
  <XCircle className="h-3 w-3 mr-1" />
  Blocked
</Badge>

<Badge variant="warning">
  <AlertCircle className="h-3 w-3 mr-1" />
  Review
</Badge>
```

### Badge in Context
```tsx
<div className="flex items-center gap-2">
  <span className="text-text-primary">Status:</span>
  <Badge variant="success">Operational</Badge>
</div>
```

## Spinner

### Loading States
```tsx
import { Spinner } from '@/components/ui';

// Small spinner
{isLoading && <Spinner size="sm" />}

// Medium spinner (default)
{isLoading && <Spinner size="md" />}

// Large spinner
{isLoading && <Spinner size="lg" />}
```

### Full Page Loading
```tsx
const LoadingPage = () => (
  <div className="flex items-center justify-center min-h-screen">
    <Spinner size="lg" />
  </div>
);
```

### Inline Loading
```tsx
<div className="flex items-center gap-2">
  <Spinner size="sm" />
  <span className="text-text-secondary">Loading data...</span>
</div>
```

## ThemeToggle

### Header with Theme Toggle
```tsx
import { ThemeToggle } from '@/components/ui';

<header className="flex items-center justify-between p-4">
  <h1 className="text-2xl font-bold">ArgusAI</h1>
  <ThemeToggle />
</header>
```

### Settings Page
```tsx
<Card title="Appearance">
  <div className="flex items-center justify-between">
    <div>
      <h4 className="font-medium text-text-primary">Theme</h4>
      <p className="text-sm text-text-secondary">
        Switch between light and dark mode
      </p>
    </div>
    <ThemeToggle />
  </div>
</Card>
```

## Complete Dashboard Example

```tsx
import {
  Card,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableCell,
  Badge,
  Button,
  Input,
  ThemeToggle,
  Spinner,
} from '@/components/ui';
import { useState, useEffect } from 'react';

const Dashboard = () => {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setIsLoading(true);
    const data = await api.getLogs();
    setLogs(data);
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-bg-primary p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-text-primary">
            Detection Dashboard
          </h1>
          <ThemeToggle />
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-3 gap-4">
          <Card title="Total Requests">
            <p className="text-3xl font-bold text-text-primary">1,234</p>
          </Card>
          <Card title="Blocked">
            <p className="text-3xl font-bold text-danger">56</p>
          </Card>
          <Card title="Success Rate">
            <p className="text-3xl font-bold text-safe">95.4%</p>
          </Card>
        </div>

        {/* Search and Actions */}
        <Card>
          <div className="flex items-center gap-4">
            <Input
              placeholder="Search logs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1"
            />
            <Button onClick={fetchLogs}>Refresh</Button>
          </div>
        </Card>

        {/* Logs Table */}
        <Card title="Recent Detections">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableCell header>Timestamp</TableCell>
                  <TableCell header>Status</TableCell>
                  <TableCell header>Layer</TableCell>
                  <TableCell header>Confidence</TableCell>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{log.timestamp}</TableCell>
                    <TableCell>
                      <Badge
                        variant={log.is_safe ? 'success' : 'danger'}
                      >
                        {log.is_safe ? 'Safe' : 'Blocked'}
                      </Badge>
                    </TableCell>
                    <TableCell>Layer {log.layer}</TableCell>
                    <TableCell>{log.confidence}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
```
