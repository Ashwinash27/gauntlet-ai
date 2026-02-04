import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

/**
 * Primary button component with multiple variants and sizes
 * @example
 * <Button variant="primary" size="md" onClick={handleClick}>Submit</Button>
 * <Button variant="danger" loading={isLoading}>Delete</Button>
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, disabled, children, className, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d1117] disabled:opacity-50 disabled:pointer-events-none';

    const variants = {
      primary: 'bg-[#58a6ff] text-[#0d1117] hover:bg-[#79b8ff] focus-visible:ring-[#58a6ff]',
      danger: 'bg-[#f85149] text-white hover:bg-[#ff6b6b] focus-visible:ring-[#f85149]',
      ghost: 'bg-transparent text-[#e6edf3] hover:bg-[#21262d] border border-[#30363d] focus-visible:ring-[#58a6ff]',
    };

    const sizes = {
      sm: 'h-8 px-3 text-sm',
      md: 'h-10 px-4 text-base',
      lg: 'h-12 px-6 text-lg',
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
