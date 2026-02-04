import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Loading spinner component with accent color
 * @example
 * <Spinner size="md" />
 * {isLoading && <Spinner size="lg" />}
 */
export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className }) => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div className="flex items-center justify-center">
      <Loader2
        className={cn('animate-spin text-[#58a6ff]', sizes[size], className)}
        aria-label="Loading"
      />
    </div>
  );
};
