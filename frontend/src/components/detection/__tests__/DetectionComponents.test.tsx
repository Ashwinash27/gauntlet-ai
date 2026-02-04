import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../StatusBadge';
import { ConfidenceGauge } from '../ConfidenceGauge';
import { LayerTimeline } from '../LayerTimeline';
import { DetectionResult } from '../DetectionResult';
import type { DetectionResult as DetectionResultType, LayerResult } from '@/types';

/**
 * Unit tests for detection visualization components
 * Run with: npm test or vitest
 */

describe('StatusBadge', () => {
  it('should render injection status correctly', () => {
    render(<StatusBadge isInjection={true} attackType="Jailbreak" />);
    expect(screen.getByText('INJECTION DETECTED')).toBeInTheDocument();
    expect(screen.getByText('Jailbreak')).toBeInTheDocument();
  });

  it('should render safe status correctly', () => {
    render(<StatusBadge isInjection={false} />);
    expect(screen.getByText('SAFE')).toBeInTheDocument();
  });

  it('should apply correct background color for injection', () => {
    const { container } = render(<StatusBadge isInjection={true} />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('bg-[#f85149]');
  });

  it('should apply correct background color for safe', () => {
    const { container } = render(<StatusBadge isInjection={false} />);
    const badge = container.firstChild;
    expect(badge).toHaveClass('bg-[#3fb950]');
  });
});

describe('ConfidenceGauge', () => {
  it('should render confidence percentage', () => {
    render(<ConfidenceGauge confidence={85} />);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('%')).toBeInTheDocument();
  });

  it('should render SVG gauge', () => {
    const { container } = render(<ConfidenceGauge confidence={50} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('should display rounded confidence value', () => {
    render(<ConfidenceGauge confidence={84.7} />);
    expect(screen.getByText('85')).toBeInTheDocument();
  });
});

describe('LayerTimeline', () => {
  const mockLayers: LayerResult[] = [
    {
      layer: 'layer_1',
      name: 'Rules',
      detected: false,
      latency_ms: 8,
      status: 'pass',
    },
    {
      layer: 'layer_2',
      name: 'Embeddings',
      detected: true,
      confidence: 87,
      latency_ms: 234,
      status: 'detected',
    },
    {
      layer: 'layer_3',
      name: 'LLM Judge',
      detected: false,
      latency_ms: 0,
      status: 'skipped',
    },
  ];

  it('should render all layers', () => {
    render(<LayerTimeline layers={mockLayers} />);
    expect(screen.getByText('Rules')).toBeInTheDocument();
    expect(screen.getByText('Embeddings')).toBeInTheDocument();
    expect(screen.getByText('LLM Judge')).toBeInTheDocument();
  });

  it('should show latency for each layer', () => {
    render(<LayerTimeline layers={mockLayers} />);
    expect(screen.getByText('8ms')).toBeInTheDocument();
    expect(screen.getByText('234ms')).toBeInTheDocument();
  });

  it('should show confidence only for detected layer', () => {
    render(<LayerTimeline layers={mockLayers} />);
    expect(screen.getByText('87%')).toBeInTheDocument();
  });

  it('should show correct status for each layer', () => {
    render(<LayerTimeline layers={mockLayers} />);
    expect(screen.getAllByText(/pass/i)).toHaveLength(1);
    expect(screen.getAllByText(/detected/i)).toHaveLength(1);
    expect(screen.getAllByText(/skipped/i)).toHaveLength(1);
  });
});

describe('DetectionResult', () => {
  const mockResult: DetectionResultType = {
    is_injection: true,
    attack_type: 'Jailbreak',
    confidence: 87,
    detecting_layer: 'layer_2',
    total_latency_ms: 242,
    layers: [
      {
        layer: 'layer_1',
        name: 'Rules',
        detected: false,
        latency_ms: 8,
        status: 'pass',
      },
      {
        layer: 'layer_2',
        name: 'Embeddings',
        detected: true,
        confidence: 87,
        latency_ms: 234,
        status: 'detected',
      },
      {
        layer: 'layer_3',
        name: 'LLM Judge',
        detected: false,
        latency_ms: 0,
        status: 'skipped',
      },
    ],
  };

  it('should render all sub-components', () => {
    render(<DetectionResult result={mockResult} />);

    // StatusBadge content
    expect(screen.getByText('INJECTION DETECTED')).toBeInTheDocument();
    expect(screen.getByText('Jailbreak')).toBeInTheDocument();

    // ConfidenceGauge
    expect(screen.getByText('87')).toBeInTheDocument();

    // LayerTimeline
    expect(screen.getByText('Rules')).toBeInTheDocument();
    expect(screen.getByText('Embeddings')).toBeInTheDocument();

    // Total latency
    expect(screen.getByText('242ms')).toBeInTheDocument();
  });

  it('should render detection flow section', () => {
    render(<DetectionResult result={mockResult} />);
    expect(screen.getByText('Detection Flow')).toBeInTheDocument();
  });

  it('should render total latency section', () => {
    render(<DetectionResult result={mockResult} />);
    expect(screen.getByText('Total Latency')).toBeInTheDocument();
  });

  it('should render timestamp if provided', () => {
    const resultWithTimestamp = {
      ...mockResult,
      timestamp: '2026-02-03T20:00:00.000Z',
    };
    render(<DetectionResult result={resultWithTimestamp} />);
    // Timestamp should be formatted and visible
    const timestampElement = screen.getByText(/2\/3\/2026|Feb|2026/);
    expect(timestampElement).toBeInTheDocument();
  });
});

describe('Integration Tests', () => {
  it('should handle safe prompt result', () => {
    const safeResult: DetectionResultType = {
      is_injection: false,
      confidence: 5,
      total_latency_ms: 1456,
      layers: [
        {
          layer: 'layer_1',
          name: 'Rules',
          detected: false,
          latency_ms: 6,
          status: 'pass',
        },
        {
          layer: 'layer_2',
          name: 'Embeddings',
          detected: false,
          latency_ms: 189,
          status: 'pass',
        },
        {
          layer: 'layer_3',
          name: 'LLM Judge',
          detected: false,
          confidence: 5,
          latency_ms: 1261,
          status: 'pass',
        },
      ],
    };

    render(<DetectionResult result={safeResult} />);
    expect(screen.getByText('SAFE')).toBeInTheDocument();
    expect(screen.getAllByText(/pass/i).length).toBeGreaterThan(0);
  });

  it('should handle layer 1 detection', () => {
    const layer1Result: DetectionResultType = {
      is_injection: true,
      attack_type: 'Direct Instruction Override',
      confidence: 95,
      detecting_layer: 'layer_1',
      total_latency_ms: 12,
      layers: [
        {
          layer: 'layer_1',
          name: 'Rules',
          detected: true,
          confidence: 95,
          latency_ms: 12,
          status: 'detected',
        },
        {
          layer: 'layer_2',
          name: 'Embeddings',
          detected: false,
          latency_ms: 0,
          status: 'skipped',
        },
        {
          layer: 'layer_3',
          name: 'LLM Judge',
          detected: false,
          latency_ms: 0,
          status: 'skipped',
        },
      ],
    };

    render(<DetectionResult result={layer1Result} />);
    expect(screen.getByText('INJECTION DETECTED')).toBeInTheDocument();
    expect(screen.getByText('Direct Instruction Override')).toBeInTheDocument();
    expect(screen.getAllByText(/skipped/i).length).toBe(2);
  });
});

/**
 * Accessibility tests
 */
describe('Accessibility', () => {
  it('StatusBadge should have proper icon elements', () => {
    const { container } = render(<StatusBadge isInjection={true} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('should use semantic HTML', () => {
    const mockResult: DetectionResultType = {
      is_injection: true,
      confidence: 85,
      total_latency_ms: 100,
      layers: [],
    };

    const { container } = render(<DetectionResult result={mockResult} />);
    expect(container.querySelector('h2')).toBeInTheDocument();
    expect(container.querySelector('h3')).toBeInTheDocument();
  });
});
