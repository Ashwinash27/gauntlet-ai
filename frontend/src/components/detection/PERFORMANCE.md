# Performance Optimization Guide

## Current Optimizations

### 1. Framer Motion Animations
- **GPU Acceleration**: All animations use `transform` and `opacity` properties which are GPU-accelerated
- **No Layout Thrashing**: Animations don't trigger layout recalculations
- **RequestAnimationFrame**: Framer Motion uses RAF for smooth 60fps animations

### 2. SVG for Graphics
- **Scalable**: ConfidenceGauge uses SVG for crisp rendering at any size
- **Small File Size**: Vector graphics are lightweight
- **CSS Styling**: Can be styled with CSS for easy theming

### 3. Component Structure
- **Composition**: Small, focused components that can be used independently
- **Props-driven**: All state comes from props, no internal state management
- **No Side Effects**: Pure components with no API calls or timers

## Recommended Optimizations

### 1. React.memo for Preventing Re-renders

Wrap components that receive complex props:

```tsx
import React from 'react';

export const ConfidenceGauge = React.memo<ConfidenceGaugeProps>(
  ({ confidence, className }) => {
    // Component code...
  },
  (prevProps, nextProps) => {
    // Custom comparison - only re-render if confidence changes significantly
    return Math.abs(prevProps.confidence - nextProps.confidence) < 1;
  }
);
```

### 2. Lazy Loading

If these components are used in a dashboard with many other components:

```tsx
// In parent component
import { lazy, Suspense } from 'react';

const DetectionResult = lazy(() =>
  import('@/components/detection').then(mod => ({ default: mod.DetectionResult }))
);

// Usage
<Suspense fallback={<LoadingSpinner />}>
  <DetectionResult result={data} />
</Suspense>
```

### 3. Memoize Expensive Calculations

For the confidence gauge color calculation:

```tsx
import { useMemo } from 'react';

const color = useMemo(() => {
  if (confidence < 30) return '#8b949e';
  if (confidence < 70) return '#f0883e';
  return '#f85149';
}, [confidence]);
```

### 4. Virtual Scrolling

If displaying multiple results in a list:

```tsx
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={results.length}
  itemSize={400}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      <DetectionResult result={results[index]} />
    </div>
  )}
</FixedSizeList>
```

### 5. Animation Performance

Reduce motion for users who prefer reduced motion:

```tsx
import { useReducedMotion } from 'framer-motion';

const shouldReduceMotion = useReducedMotion();

<motion.div
  animate={shouldReduceMotion ? {} : { opacity: [0.5, 0.8, 0.5] }}
>
```

### 6. Code Splitting by Route

If detection results are on a specific route:

```tsx
// router.tsx
const DetectionDashboard = lazy(() => import('./pages/DetectionDashboard'));

<Route path="/detection" element={
  <Suspense fallback={<LoadingPage />}>
    <DetectionDashboard />
  </Suspense>
} />
```

## Performance Budgets

### Target Metrics
- **Initial Load**: < 100ms (components are lightweight)
- **Animation FPS**: 60fps (GPU-accelerated)
- **Re-render Time**: < 16ms
- **Bundle Size**: ~15KB gzipped (including framer-motion)

### Measuring Performance

```tsx
import { Profiler } from 'react';

<Profiler id="DetectionResult" onRender={onRenderCallback}>
  <DetectionResult result={data} />
</Profiler>

function onRenderCallback(
  id,
  phase,
  actualDuration,
  baseDuration,
  startTime,
  commitTime
) {
  console.log(`${id} ${phase} render took ${actualDuration}ms`);
}
```

### Chrome DevTools Performance

1. Open Chrome DevTools
2. Go to Performance tab
3. Record while interacting with components
4. Look for:
   - Long tasks (>50ms)
   - Layout shifts
   - Paint operations
   - Animation frame drops

## Memory Optimization

### 1. Avoid Memory Leaks

Components are pure and don't:
- Create timers or intervals
- Subscribe to events
- Store references to DOM nodes

### 2. Clean Up Animations

Framer Motion handles cleanup automatically, but if you add custom effects:

```tsx
useEffect(() => {
  const animation = animate(/* ... */);

  return () => {
    animation.stop();
  };
}, []);
```

## Bundle Size

### Current Dependencies
- `framer-motion`: ~50KB gzipped
- `lucide-react`: ~1KB per icon (tree-shakeable)
- `tailwind-merge` + `clsx`: ~2KB gzipped

### Tree Shaking

Import only what you need:

```tsx
// Good - tree-shakeable
import { Shield, ShieldAlert } from 'lucide-react';

// Avoid - imports entire library
import * as Icons from 'lucide-react';
```

## Network Performance

### 1. Preload Fonts

If using JetBrains Mono:

```html
<link rel="preload" href="/fonts/jetbrains-mono.woff2" as="font" type="font/woff2" crossorigin>
```

### 2. Image Optimization

Icons are SVG (optimal), but if you add raster images:
- Use WebP format
- Lazy load with `loading="lazy"`
- Use responsive images with `srcset`

## Accessibility Performance

### Focus Management

```tsx
// Add focus indicators without layout shift
.focus-visible:ring-2 {
  outline: 2px solid;
  outline-offset: 2px;
}
```

### Reduce Motion

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Monitoring

### Core Web Vitals

Track these metrics:
- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1

### Custom Metrics

```tsx
// Track detection result render time
const startTime = performance.now();
render(<DetectionResult result={data} />);
const endTime = performance.now();
console.log(`Render time: ${endTime - startTime}ms`);
```

## Production Build

```bash
# Build with production optimizations
npm run build

# Analyze bundle
npm install --save-dev vite-plugin-bundle-analyzer
# Add to vite.config.ts
```

## Summary

These components are already optimized for performance with:
- GPU-accelerated animations
- No unnecessary re-renders
- Lightweight SVG graphics
- Minimal dependencies
- Pure, composable architecture

For production use, consider adding:
- React.memo for complex props
- Lazy loading for code splitting
- Virtual scrolling for large lists
- Performance monitoring
