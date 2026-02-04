import React, { useState } from 'react';
import {
  Button,
  Input,
  Card,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableCell,
  Modal,
  ThemeToggle,
  Spinner,
  Badge,
} from './index';
import { AlertCircle, CheckCircle, ShieldAlert } from 'lucide-react';

/**
 * Component showcase for testing and documentation
 * Demonstrates all UI components in the Night Operations theme
 */
export const ComponentShowcase: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState('');
  const [_isLoading, setIsLoading] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    if (e.target.value.length > 0) {
      setInputError('');
    }
  };

  const handleSubmit = () => {
    if (!inputValue) {
      setInputError('This field is required');
      return;
    }
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 2000);
  };

  return (
    <div className="min-h-screen bg-bg-primary p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">
              ArgusAI UI Components
            </h1>
            <p className="text-text-secondary">Night Operations Design System</p>
          </div>
          <ThemeToggle />
        </div>

        {/* Buttons */}
        <Card title="Buttons">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <Button variant="primary" size="sm">Primary Small</Button>
              <Button variant="primary" size="md">Primary Medium</Button>
              <Button variant="primary" size="lg">Primary Large</Button>
            </div>
            <div className="flex flex-wrap gap-4">
              <Button variant="danger" size="md">Danger</Button>
              <Button variant="ghost" size="md">Ghost</Button>
              <Button variant="primary" size="md" disabled>Disabled</Button>
              <Button variant="primary" size="md" loading>Loading</Button>
            </div>
          </div>
        </Card>

        {/* Inputs */}
        <Card title="Inputs">
          <div className="space-y-4 max-w-md">
            <Input
              label="API Key"
              placeholder="Enter your API key"
              value={inputValue}
              onChange={handleInputChange}
              error={inputError}
            />
            <Input
              label="Email"
              type="email"
              placeholder="your@email.com"
            />
            <Input
              label="Disabled Input"
              placeholder="Cannot edit"
              disabled
              value="Disabled value"
            />
            <Button onClick={handleSubmit} variant="primary">
              Submit
            </Button>
          </div>
        </Card>

        {/* Badges */}
        <Card title="Badges">
          <div className="flex flex-wrap gap-3">
            <Badge variant="success">
              <CheckCircle className="h-3 w-3 mr-1" />
              Safe
            </Badge>
            <Badge variant="danger">
              <ShieldAlert className="h-3 w-3 mr-1" />
              Injection Detected
            </Badge>
            <Badge variant="warning">
              <AlertCircle className="h-3 w-3 mr-1" />
              Suspicious
            </Badge>
            <Badge variant="info">Layer 2</Badge>
            <Badge variant="neutral">Pending</Badge>
          </div>
        </Card>

        {/* Table */}
        <Card title="Detection Log">
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
              <TableRow>
                <TableCell>2026-02-03 14:32:01</TableCell>
                <TableCell>
                  <Badge variant="success">Safe</Badge>
                </TableCell>
                <TableCell>Layer 1</TableCell>
                <TableCell>98.2%</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>2026-02-03 14:31:45</TableCell>
                <TableCell>
                  <Badge variant="danger">Blocked</Badge>
                </TableCell>
                <TableCell>Layer 2</TableCell>
                <TableCell>94.7%</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>2026-02-03 14:30:22</TableCell>
                <TableCell>
                  <Badge variant="warning">Review</Badge>
                </TableCell>
                <TableCell>Layer 3</TableCell>
                <TableCell>87.3%</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>

        {/* Spinner */}
        <Card title="Loading States">
          <div className="flex items-center gap-8">
            <div className="text-center">
              <Spinner size="sm" />
              <p className="text-text-secondary text-sm mt-2">Small</p>
            </div>
            <div className="text-center">
              <Spinner size="md" />
              <p className="text-text-secondary text-sm mt-2">Medium</p>
            </div>
            <div className="text-center">
              <Spinner size="lg" />
              <p className="text-text-secondary text-sm mt-2">Large</p>
            </div>
          </div>
        </Card>

        {/* Modal */}
        <Card title="Modal">
          <Button onClick={() => setIsModalOpen(true)} variant="primary">
            Open Modal
          </Button>

          <Modal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            title="Confirm Action"
          >
            <div className="space-y-4">
              <p className="text-text-primary">
                Are you sure you want to proceed with this action?
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="ghost"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setIsModalOpen(false)}
                >
                  Confirm
                </Button>
              </div>
            </div>
          </Modal>
        </Card>

        {/* Color Palette Reference */}
        <Card title="Color Palette">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="h-20 bg-bg-primary rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">bg-primary</p>
            </div>
            <div>
              <div className="h-20 bg-bg-secondary rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">bg-secondary</p>
            </div>
            <div>
              <div className="h-20 bg-bg-tertiary rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">bg-tertiary</p>
            </div>
            <div>
              <div className="h-20 bg-safe rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">safe</p>
            </div>
            <div>
              <div className="h-20 bg-danger rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">danger</p>
            </div>
            <div>
              <div className="h-20 bg-warning rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">warning</p>
            </div>
            <div>
              <div className="h-20 bg-accent rounded border border-[#30363d]"></div>
              <p className="text-text-secondary text-sm mt-2">accent</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
