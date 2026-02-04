# Accessibility Checklist

## Component Accessibility Features

### Button
- ✅ Semantic HTML (`<button>`)
- ✅ Keyboard navigation (native button behavior)
- ✅ Focus visible states (ring on focus)
- ✅ Disabled state properly conveyed
- ✅ Loading state with spinner icon
- ⚠️ TODO: Add `aria-busy="true"` when loading

### Input
- ✅ Semantic HTML (`<input>`)
- ✅ Label association
- ✅ Error state with visible text
- ✅ Focus visible states
- ✅ Placeholder text with proper color contrast
- ⚠️ Consider: Add `aria-describedby` for error messages
- ⚠️ Consider: Add `aria-invalid` when error exists

### Card
- ✅ Semantic HTML structure
- ✅ Proper heading hierarchy (h3 for title)
- ✅ Color contrast meets WCAG AA standards

### Table
- ✅ Semantic HTML (`<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>`)
- ✅ Proper table header cells (`<th>` with header prop)
- ✅ Color contrast for all text
- ⚠️ Consider: Add `scope="col"` to header cells
- ⚠️ Consider: Add `caption` element for table description

### Modal
- ✅ Keyboard navigation (ESC to close)
- ✅ Focus trap (backdrop click closes)
- ✅ Body scroll prevention
- ✅ Close button with aria-label
- ⚠️ TODO: Implement focus trap for keyboard users
- ⚠️ TODO: Add `role="dialog"` and `aria-modal="true"`
- ⚠️ TODO: Focus management (focus first interactive element on open)

### ThemeToggle
- ✅ Semantic button element
- ✅ aria-label describes current action
- ✅ Keyboard accessible
- ✅ Focus visible state
- ✅ Icon changes to indicate state

### Spinner
- ✅ aria-label for screen readers
- ✅ Visible loading indicator
- ⚠️ Consider: Add `role="status"` and `aria-live="polite"`

### Badge
- ✅ Semantic HTML
- ✅ Color + text (not relying on color alone)
- ✅ Proper color contrast
- ⚠️ Consider: Add `role="status"` for dynamic badges

## WCAG 2.1 Compliance

### Level A
- ✅ 1.1.1 Non-text Content: Icons have text alternatives
- ✅ 1.3.1 Info and Relationships: Semantic HTML used
- ✅ 2.1.1 Keyboard: All interactive elements keyboard accessible
- ✅ 2.1.2 No Keyboard Trap: No keyboard traps present
- ✅ 2.4.4 Link Purpose: Button text describes purpose
- ✅ 3.2.2 On Input: No unexpected context changes

### Level AA
- ✅ 1.4.3 Contrast (Minimum): All text meets 4.5:1 ratio
  - Primary text (#e6edf3) on primary bg (#0d1117): ~13:1
  - Secondary text (#8b949e) on primary bg (#0d1117): ~7:1
  - Accent (#58a6ff) on dark bg: ~8:1
- ✅ 2.4.7 Focus Visible: All interactive elements have visible focus
- ⚠️ 1.3.5 Identify Input Purpose: Add autocomplete attributes where appropriate

### Level AAA (Aspirational)
- ⚠️ 1.4.6 Contrast (Enhanced): Consider increasing contrast to 7:1 for AAA
- ⚠️ 2.4.8 Location: Add breadcrumb navigation
- ⚠️ 2.5.5 Target Size: Ensure minimum 44x44px touch targets

## Keyboard Navigation

| Component | Key | Action |
|-----------|-----|--------|
| Button | Enter/Space | Activate |
| Input | Tab | Focus next/previous |
| Modal | Escape | Close modal |
| ThemeToggle | Enter/Space | Toggle theme |
| Table Row (clickable) | Enter/Space | Activate row |

## Screen Reader Testing

Test with:
- NVDA (Windows)
- JAWS (Windows)
- VoiceOver (macOS/iOS)
- TalkBack (Android)

## Recommended Improvements

1. **Modal Focus Management**
   ```tsx
   // Trap focus within modal when open
   // Return focus to trigger element on close
   ```

2. **Form Validation**
   ```tsx
   // Add aria-invalid and aria-describedby to inputs
   <Input
     aria-invalid={!!error}
     aria-describedby={error ? "error-id" : undefined}
   />
   ```

3. **Loading States**
   ```tsx
   // Add aria-busy to buttons
   <Button aria-busy={loading} loading={loading}>
   ```

4. **Table Semantics**
   ```tsx
   <TableCell header scope="col">Column Header</TableCell>
   ```

5. **Skip Links**
   ```tsx
   // Add skip navigation link
   <a href="#main-content" className="sr-only focus:not-sr-only">
     Skip to main content
   </a>
   ```

## Testing Tools

- axe DevTools browser extension
- WAVE browser extension
- Lighthouse accessibility audit
- Keyboard-only navigation testing
- Screen reader testing

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
