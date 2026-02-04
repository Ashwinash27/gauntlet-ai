import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

type BadgeVariant = 'cyan' | 'magenta' | 'safe' | 'danger' | 'warning' | 'layer1' | 'layer2' | 'layer3';

interface NeonBadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  pulse?: boolean;
  className?: string;
}

const variantStyles: Record<BadgeVariant, { border: string; text: string; glow: string; bg: string }> = {
  cyan: {
    border: 'border-neon-cyan/50',
    text: 'text-neon-cyan',
    glow: 'shadow-neon-cyan',
    bg: 'bg-neon-cyan/10',
  },
  magenta: {
    border: 'border-neon-magenta/50',
    text: 'text-neon-magenta',
    glow: 'shadow-neon-magenta',
    bg: 'bg-neon-magenta/10',
  },
  safe: {
    border: 'border-status-safe/50',
    text: 'text-status-safe',
    glow: 'shadow-neon-safe',
    bg: 'bg-status-safe/10',
  },
  danger: {
    border: 'border-status-danger/50',
    text: 'text-status-danger',
    glow: 'shadow-neon-danger',
    bg: 'bg-status-danger/10',
  },
  warning: {
    border: 'border-status-warning/50',
    text: 'text-status-warning',
    glow: 'shadow-neon-warning',
    bg: 'bg-status-warning/10',
  },
  layer1: {
    border: 'border-layer-1/50',
    text: 'text-layer-1',
    glow: 'shadow-neon-layer-1',
    bg: 'bg-layer-1/10',
  },
  layer2: {
    border: 'border-layer-2/50',
    text: 'text-layer-2',
    glow: 'shadow-neon-layer-2',
    bg: 'bg-layer-2/10',
  },
  layer3: {
    border: 'border-layer-3/50',
    text: 'text-layer-3',
    glow: 'shadow-neon-layer-3',
    bg: 'bg-layer-3/10',
  },
};

/**
 * Neon-styled badge with glow effects.
 */
export function NeonBadge({ variant = 'cyan', children, pulse = false, className }: NeonBadgeProps) {
  const styles = variantStyles[variant];

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'inline-flex items-center px-2 py-0.5 text-xs uppercase tracking-wider',
        'border font-mono',
        styles.border,
        styles.text,
        styles.bg,
        pulse && styles.glow,
        pulse && 'animate-glow-pulse',
        className
      )}
    >
      {pulse && (
        <span className={cn('w-1.5 h-1.5 rounded-full mr-2', styles.text.replace('text-', 'bg-'))} />
      )}
      {children}
    </motion.span>
  );
}
