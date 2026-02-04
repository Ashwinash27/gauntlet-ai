import { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface NeonInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

/**
 * Neon-styled input with glow focus states.
 */
export const NeonInput = forwardRef<HTMLInputElement, NeonInputProps>(
  ({ label, error, icon, className, ...props }, ref) => {
    return (
      <div className="space-y-1">
        {label && (
          <label className="block text-xs uppercase tracking-wider text-text-secondary">
            {label}
          </label>
        )}
        <div className="relative group">
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            className={cn(
              'w-full bg-void-base border border-neon-cyan/20 rounded-none',
              'px-4 py-3 text-text-primary placeholder:text-text-tertiary',
              'transition-all duration-300',
              'focus:border-neon-cyan focus:shadow-neon-cyan focus:outline-none focus:scale-[1.01]',
              'hover:border-neon-cyan/40',
              icon && 'pl-10',
              error && 'border-status-danger focus:border-status-danger focus:shadow-neon-danger',
              className
            )}
            {...props}
          />

          {/* Glow effect on focus */}
          <div
            className={cn(
              'absolute inset-0 pointer-events-none opacity-0 transition-opacity duration-300',
              'bg-gradient-to-r from-neon-cyan/5 via-transparent to-neon-cyan/5',
              'group-focus-within:opacity-100'
            )}
          />
        </div>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-status-danger"
          >
            {error}
          </motion.p>
        )}
      </div>
    );
  }
);

NeonInput.displayName = 'NeonInput';
