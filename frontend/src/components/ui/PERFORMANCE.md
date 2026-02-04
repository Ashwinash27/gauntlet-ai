# Performance Optimization Guide

## Component Performance

### Current Optimizations

1. **React.forwardRef**
   - Button and Input components use forwardRef for better ref handling
   - No unnecessary re-renders from ref changes

2. **Static Tailwind Classes**
   - All styling uses static Tailwind classes
   - No runtime CSS generation
   - Minimal bundle size impact

3. **Tree Shaking**
   - Barrel exports allow for optimal tree shaking
   - Import only what you need

4. **No External Dependencies**
   - Only uses React, lucide-react, framer-motion, clsx, tailwind-merge
   - Small bundle footprint

### Recommended Optimizations

#### 1. Code Splitting
```tsx
// Lazy load showcase component
const ComponentShowcase = React.lazy(() =>
  import('./ComponentShowcase')
);

// Usage with Suspense
<Suspense fallback={<Spinner size="lg" />}>
  <ComponentShowcase />
</Suspense>
```

#### 2. Memoization
```tsx
// Memoize expensive computations
import React, { useMemo } from 'react';

const MemoizedTable = React.memo(({ data }) => {
  const sortedData = useMemo(
    () => data.sort((a, b) => a.timestamp - b.timestamp),
    [data]
  );

  return <Table>{/* render sortedData */}</Table>;
});
```

#### 3. Virtual Scrolling for Large Tables
```tsx
// For tables with 100+ rows, use react-window
import { FixedSizeList } from 'react-window';

const VirtualTable = ({ rows }) => (
  <FixedSizeList
    height={400}
    itemCount={rows.length}
    itemSize={48}
  >
    {({ index, style }) => (
      <TableRow style={style}>{rows[index]}</TableRow>
    )}
  </FixedSizeList>
);
```

#### 4. Debounce Input Changes
```tsx
// Debounce search/filter inputs
import { useDebouncedCallback } from 'use-debounce';

const SearchInput = () => {
  const debouncedSearch = useDebouncedCallback(
    (value) => performSearch(value),
    300
  );

  return (
    <Input
      onChange={(e) => debouncedSearch(e.target.value)}
      placeholder="Search..."
    />
  );
};
```

#### 5. Modal Animation Optimization
```tsx
// Reduce motion for users who prefer it
const Modal = ({ isOpen, onClose, children }) => {
  const prefersReducedMotion = useMediaQuery(
    '(prefers-reduced-motion: reduce)'
  );

  const transition = prefersReducedMotion
    ? { duration: 0 }
    : { duration: 0.2 };

  return (
    <motion.div transition={transition}>
      {children}
    </motion.div>
  );
};
```

## Performance Budgets

### Target Metrics
- First Contentful Paint (FCP): < 1.5s
- Largest Contentful Paint (LCP): < 2.5s
- Time to Interactive (TTI): < 3.0s
- Cumulative Layout Shift (CLS): < 0.1
- First Input Delay (FID): < 100ms

### Bundle Size Targets
- Initial JS bundle: < 200KB (gzipped)
- CSS bundle: < 20KB (gzipped)
- Total page weight: < 500KB

### Current Bundle Impact
```bash
# Measure component bundle size
npm run build -- --mode production
# Check dist/assets for bundle sizes
```

## Image Optimization

### Icon Usage
- Use SVG icons from lucide-react (tree-shakeable)
- Avoid icon fonts for better performance
- Icons are lazy-loaded by bundler

### Future Image Guidelines
```tsx
// Use next-gen formats and lazy loading
<img
  src="image.webp"
  alt="Description"
  loading="lazy"
  decoding="async"
  width={400}
  height={300}
/>
```

## Network Performance

### API Call Optimization
```tsx
// Use SWR or React Query for data fetching
import useSWR from 'swr';

const Dashboard = () => {
  const { data, error } = useSWR('/api/stats', fetcher, {
    refreshInterval: 30000, // Refresh every 30s
    revalidateOnFocus: false,
  });

  if (!data) return <Spinner size="lg" />;
  return <Card>{/* render data */}</Card>;
};
```

### Request Batching
```tsx
// Batch multiple API calls
const fetchDashboardData = async () => {
  const [stats, logs, settings] = await Promise.all([
    fetch('/api/stats'),
    fetch('/api/logs'),
    fetch('/api/settings'),
  ]);
  return { stats, logs, settings };
};
```

## Runtime Performance

### Avoid Inline Functions in Render
```tsx
// Bad - creates new function on every render
<Button onClick={() => handleClick(id)}>Click</Button>

// Good - use useCallback
const handleClickWithId = useCallback(
  () => handleClick(id),
  [id, handleClick]
);
<Button onClick={handleClickWithId}>Click</Button>
```

### Optimize List Rendering
```tsx
// Always use keys for lists
{items.map((item) => (
  <TableRow key={item.id}>
    <TableCell>{item.name}</TableCell>
  </TableRow>
))}

// For very large lists, use virtual scrolling
```

## CSS Performance

### Tailwind Purge
```js
// tailwind.config.js already configured for purging
content: [
  "./index.html",
  "./src/**/*.{js,ts,jsx,tsx}",
],
```

### Avoid Dynamic Classes
```tsx
// Bad - creates new class combinations
const dynamicClass = `bg-${color}-500`;

// Good - use predefined classes with cn()
const classes = cn(
  'base-class',
  color === 'red' && 'bg-danger',
  color === 'green' && 'bg-safe'
);
```

## Monitoring

### Performance Metrics
```tsx
// Add performance monitoring
import { useEffect } from 'react';

const reportWebVitals = (metric) => {
  // Send to analytics
  console.log(metric);
};

// In main.tsx
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

getCLS(reportWebVitals);
getFID(reportWebVitals);
getFCP(reportWebVitals);
getLCP(reportWebVitals);
getTTFB(reportWebVitals);
```

### React DevTools Profiler
```bash
# Profile component renders
# Open React DevTools > Profiler
# Record a session and analyze render times
```

## Production Checklist

- [ ] Enable production build (`npm run build`)
- [ ] Enable gzip/brotli compression on server
- [ ] Set proper cache headers for static assets
- [ ] Use CDN for static assets
- [ ] Enable tree shaking in bundler
- [ ] Remove console.logs in production
- [ ] Lazy load non-critical components
- [ ] Implement code splitting for routes
- [ ] Monitor Core Web Vitals
- [ ] Run Lighthouse audit (target score > 90)

## Testing Performance

```bash
# Run Lighthouse in CI
npm install -g lighthouse
lighthouse https://your-app.com --view

# Measure bundle size
npm run build
ls -lh dist/assets

# Analyze bundle composition
npm install -g source-map-explorer
source-map-explorer dist/assets/*.js
```

## Quick Wins

1. Lazy load Modal and ComponentShowcase
2. Add `loading="lazy"` to images below the fold
3. Debounce search/filter inputs
4. Use React.memo for expensive list items
5. Enable production build optimizations
6. Compress assets with gzip/brotli
7. Use CDN for static files
8. Implement service worker for caching

## Resources

- [Web Vitals](https://web.dev/vitals/)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [Lighthouse Documentation](https://developer.chrome.com/docs/lighthouse/)
- [Bundle Size Analysis](https://bundlephobia.com/)
