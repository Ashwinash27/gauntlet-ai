import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';
import { CountUp } from '../animations/CountUp';

type PanelVariant = 'cyan' | 'magenta' | 'safe' | 'danger' | 'warning';

interface DataPanelProps {
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  variant?: PanelVariant;
  icon?: React.ReactNode;
  trend?: { value: number; direction: 'up' | 'down' };
  className?: string;
}

const variantStyles: Record<PanelVariant, { border: string; text: string; glow: string }> = {
  cyan: {
    border: 'border-neon-cyan/30',
    text: 'text-neon-cyan',
    glow: 'group-hover:shadow-neon-cyan',
  },
  magenta: {
    border: 'border-neon-magenta/30',
    text: 'text-neon-magenta',
    glow: 'group-hover:shadow-neon-magenta',
  },
  safe: {
    border: 'border-status-safe/30',
    text: 'text-status-safe',
    glow: 'group-hover:shadow-neon-safe',
  },
  danger: {
    border: 'border-status-danger/30',
    text: 'text-status-danger',
    glow: 'group-hover:shadow-neon-danger',
  },
  warning: {
    border: 'border-status-warning/30',
    text: 'text-status-warning',
    glow: 'group-hover:shadow-neon-warning',
  },
};

/**
 * Stats card with animated count-up and glow effects.
 */
export function DataPanel({
  label,
  value,
  suffix = '',
  prefix = '',
  decimals = 0,
  variant = 'cyan',
  icon,
  trend,
  className,
}: DataPanelProps) {
  const styles = variantStyles[variant];

  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      className={cn(
        'group relative bg-void-elevated border p-6 transition-all duration-300',
        styles.border,
        styles.glow,
        className
      )}
    >
      {/* Corner accents */}
      <div className={cn('absolute top-0 left-0 w-2 h-2 border-t border-l', styles.border)} />
      <div className={cn('absolute top-0 right-0 w-2 h-2 border-t border-r', styles.border)} />
      <div className={cn('absolute bottom-0 left-0 w-2 h-2 border-b border-l', styles.border)} />
      <div className={cn('absolute bottom-0 right-0 w-2 h-2 border-b border-r', styles.border)} />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">{label}</p>
          <div className={cn('text-3xl font-display font-bold', styles.text)}>
            <CountUp
              end={value}
              duration={1.5}
              decimals={decimals}
              prefix={prefix}
              suffix={suffix}
            />
          </div>
          {trend && (
            <p
              className={cn(
                'text-xs mt-2',
                trend.direction === 'up' ? 'text-status-safe' : 'text-status-danger'
              )}
            >
              {trend.direction === 'up' ? '+' : '-'}
              {trend.value}% from last period
            </p>
          )}
        </div>
        {icon && (
          <div className={cn('p-2 border', styles.border, 'opacity-50 group-hover:opacity-100')}>
            {icon}
          </div>
        )}
      </div>

      {/* Bottom accent line */}
      <motion.div
        className={cn('absolute bottom-0 left-0 h-0.5', styles.text.replace('text-', 'bg-'))}
        initial={{ width: '0%' }}
        whileInView={{ width: '100%' }}
        transition={{ duration: 0.8, delay: 0.2 }}
      />
    </motion.div>
  );
}
