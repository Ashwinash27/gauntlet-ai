import React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

/**
 * Text input component with optional label and error state
 * @example
 * <Input label="API Key" placeholder="Enter your API key" value={apiKey} onChange={handleChange} />
 * <Input type="email" error="Invalid email format" />
 */
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, type = 'text', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-[#e6edf3] mb-2">
            {label}
          </label>
        )}
        <input
          ref={ref}
          type={type}
          className={cn(
            'w-full h-10 px-3 py-2 text-[#e6edf3] bg-[#21262d] border border-[#30363d] rounded-md',
            'placeholder:text-[#8b949e]',
            'focus:outline-none focus:ring-2 focus:ring-[#58a6ff] focus:border-transparent',
            'transition-colors',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error && 'border-[#f85149] focus:ring-[#f85149]',
            className
          )}
          {...props}
        />
        {error && (
          <p className="mt-1 text-sm text-[#f85149]">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
