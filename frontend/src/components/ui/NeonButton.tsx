import { cn } from '../../lib/utils';

type ButtonVariant = 'cyan' | 'magenta' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface NeonButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  glow?: boolean;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  cyan: `
    border-neon-cyan text-neon-cyan
    hover:bg-neon-cyan/10 hover:shadow-neon-cyan
    active:bg-neon-cyan/20
  `,
  magenta: `
    border-neon-magenta text-neon-magenta
    hover:bg-neon-magenta/10 hover:shadow-neon-magenta
    active:bg-neon-magenta/20
  `,
  danger: `
    border-status-danger text-status-danger
    hover:bg-status-danger/10 hover:shadow-neon-danger
    active:bg-status-danger/20
  `,
  ghost: `
    border-transparent text-text-secondary
    hover:text-text-primary hover:border-neon-cyan/30
    active:bg-neon-cyan/5
  `,
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

/**
 * Neon-styled button with glow effects and loading state.
 */
export function NeonButton({
  variant = 'cyan',
  size = 'md',
  loading = false,
  glow = false,
  disabled,
  className,
  children,
  ...props
}: NeonButtonProps) {
  return (
    <button
      className={cn(
        'relative border font-mono uppercase tracking-wider',
        'transition-all duration-300 ease-out',
        'hover:scale-[1.02] active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
        variantStyles[variant],
        sizeStyles[size],
        glow && variant === 'cyan' && 'shadow-neon-cyan',
        glow && variant === 'magenta' && 'shadow-neon-magenta',
        glow && variant === 'danger' && 'shadow-neon-danger',
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {/* Loading data stream effect */}
      {loading && (
        <div
          className="absolute inset-0 data-stream opacity-50"
          style={{
            backgroundImage: `linear-gradient(
              45deg,
              transparent 25%,
              rgba(0, 240, 255, 0.2) 25%,
              rgba(0, 240, 255, 0.2) 50%,
              transparent 50%,
              transparent 75%,
              rgba(0, 240, 255, 0.2) 75%
            )`,
            backgroundSize: '20px 20px',
          }}
        />
      )}

      <span className={cn('relative z-10 flex items-center justify-center gap-2', loading && 'opacity-70')}>
        {loading && (
          <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {children}
      </span>
    </button>
  );
}
