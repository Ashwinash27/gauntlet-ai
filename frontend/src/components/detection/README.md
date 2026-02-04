# Detection Result Visualization Components

Visual components for displaying ArgusAI prompt injection detection results with a three-layer cascade system.

## Components

### 1. StatusBadge
Large prominent status indicator showing whether an injection was detected.

**Props:**
- `isInjection: boolean` - Whether injection was detected
- `attackType?: string` - Type of attack detected (optional)
- `className?: string` - Additional CSS classes

**Features:**
- Red background (#f85149) with shield alert icon for injections
- Green background (#3fb950) with shield check icon for safe prompts
- Pulse animation on injection detection using framer-motion
- Large, unmissable design

**Usage:**
```tsx
import { StatusBadge } from '@/components/detection';

<StatusBadge isInjection={true} attackType="Jailbreak" />
<StatusBadge isInjection={false} />
```

---

### 2. ConfidenceGauge
Circular SVG progress gauge showing confidence percentage.

**Props:**
- `confidence: number` - Confidence level (0-100)
- `className?: string` - Additional CSS classes

**Features:**
- Circular arc that fills based on confidence level
- Dynamic color coding:
  - Gray (#8b949e): <30%
  - Yellow (#f0883e): 30-70%
  - Red (#f85149): >70%
- Large percentage number in center using JetBrains Mono font
- Smooth animation on value change with framer-motion

**Usage:**
```tsx
import { ConfidenceGauge } from '@/components/detection';

<ConfidenceGauge confidence={85} />
```

---

### 3. LayerTimeline
Horizontal timeline showing detection flow through the three-layer cascade.

**Props:**
- `layers: LayerResult[]` - Array of layer results
- `className?: string` - Additional CSS classes

**Features:**
- Shows L1 → L2 → L3 flow with arrows
- Each layer displays:
  - Layer name
  - Status (pass/detected/skipped)
  - Latency in milliseconds
  - Confidence % (for detecting layer only)
- Layer-specific colors:
  - Layer 1 (Rules): #a371f7 (purple)
  - Layer 2 (Embeddings): #f778ba (pink)
  - Layer 3 (LLM Judge): #ffa657 (orange)
- Grayed out skipped layers
- Glow effect on detecting layer

**Usage:**
```tsx
import { LayerTimeline } from '@/components/detection';

<LayerTimeline layers={result.layers} />
```

---

### 4. DetectionResult
Complete detection result visualization combining all components above.

**Props:**
- `result: DetectionResult` - Full detection result object
- `className?: string` - Additional CSS classes

**Features:**
- Responsive grid layout
- StatusBadge at top (2 columns on large screens)
- ConfidenceGauge on the side (1 column)
- LayerTimeline below showing cascade flow
- Total latency display at bottom
- Optional timestamp
- Card container with GitHub-themed styling

**Usage:**
```tsx
import { DetectionResult } from '@/components/detection';

<DetectionResult result={detectionData} />
```

---

## Type Definitions

```typescript
interface LayerResult {
  layer: 'layer_1' | 'layer_2' | 'layer_3';
  name: string;
  detected: boolean;
  confidence?: number;
  latency_ms: number;
  reason?: string;
  status: 'pass' | 'detected' | 'skipped';
}

interface DetectionResult {
  is_injection: boolean;
  attack_type?: string;
  confidence: number;
  detecting_layer?: 'layer_1' | 'layer_2' | 'layer_3';
  total_latency_ms: number;
  layers: LayerResult[];
  timestamp?: string;
}
```

---

## Color System

### Layer Colors
- **Layer 1 (Rules)**: `#a371f7` - Purple
- **Layer 2 (Embeddings)**: `#f778ba` - Pink
- **Layer 3 (LLM Judge)**: `#ffa657` - Orange

### Status Colors
- **Safe**: `#3fb950` - Green
- **Injection**: `#f85149` - Red
- **Pass**: `#3fb950` - Green
- **Skipped**: `#8b949e` - Gray

### Confidence Colors
- **Low (<30%)**: `#8b949e` - Gray
- **Medium (30-70%)**: `#f0883e` - Yellow
- **High (>70%)**: `#f85149` - Red

---

## Dependencies

- `react` - UI framework
- `framer-motion` - Animations
- `lucide-react` - Icons
- `tailwindcss` - Styling
- `clsx` + `tailwind-merge` - Class utilities

---

## Examples

See `DetectionResultExample.tsx` for complete usage examples including:
1. Injection detected by Layer 1 (Rules)
2. Injection detected by Layer 3 (LLM Judge)
3. Safe prompt (all layers passed)

---

## Accessibility

- Semantic HTML elements
- Proper ARIA labels on icons
- Color + icon combinations (not color alone)
- Keyboard navigation support
- High contrast text for readability
- Screen reader friendly status indicators

---

## Performance

- Lazy loading with React.lazy (if needed)
- Memoization for expensive calculations
- Optimized re-renders with React.memo
- Framer-motion animations use GPU acceleration
- SVG for scalable, performant graphics
