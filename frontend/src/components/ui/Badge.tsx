import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps {
  variant?: 'success' | 'danger' | 'warning' | 'info' | 'neutral';
  children: React.ReactNode;
  className?: string;
}

/**
 * Badge component for status indicators and tags
 * @example
 * <Badge variant="success">Safe</Badge>
 * <Badge variant="danger">Injection Detected</Badge>
 * <Badge variant="warning">Suspicious</Badge>
 */
export const Badge: React.FC<BadgeProps> = ({ variant = 'neutral', children, className }) => {
  const baseStyles = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';

  const variants = {
    success: 'bg-[#3fb950]/10 text-[#3fb950] border border-[#3fb950]/20',
    danger: 'bg-[#f85149]/10 text-[#f85149] border border-[#f85149]/20',
    warning: 'bg-[#d29922]/10 text-[#d29922] border border-[#d29922]/20',
    info: 'bg-[#58a6ff]/10 text-[#58a6ff] border border-[#58a6ff]/20',
    neutral: 'bg-[#8b949e]/10 text-[#8b949e] border border-[#8b949e]/20',
  };

  return (
    <span className={cn(baseStyles, variants[variant], className)}>
      {children}
    </span>
  );
};
