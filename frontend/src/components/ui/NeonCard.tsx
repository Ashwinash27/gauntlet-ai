import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface NeonCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'cyan' | 'magenta';
  hover?: boolean;
  borderScan?: boolean;
}

/**
 * Card with neon border effects.
 */
export function NeonCard({
  children,
  className,
  variant = 'default',
  hover = true,
  borderScan = false,
}: NeonCardProps) {
  const borderColor = {
    default: 'border-neon-cyan/10 hover:border-neon-cyan/30',
    cyan: 'border-neon-cyan/30 hover:border-neon-cyan/50',
    magenta: 'border-neon-magenta/30 hover:border-neon-magenta/50',
  };

  const glowColor = {
    default: 'hover:shadow-[0_0_30px_rgba(0,240,255,0.1)]',
    cyan: 'hover:shadow-neon-cyan',
    magenta: 'hover:shadow-neon-magenta',
  };

  return (
    <motion.div
      whileHover={hover ? { y: -4 } : undefined}
      className={cn(
        'relative bg-void-elevated border transition-all duration-300',
        borderColor[variant],
        hover && glowColor[variant],
        borderScan && 'border-scan',
        className
      )}
    >
      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t border-l border-neon-cyan/50" />
      <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-neon-cyan/50" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-neon-cyan/50" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-neon-cyan/50" />

      {children}
    </motion.div>
  );
}
