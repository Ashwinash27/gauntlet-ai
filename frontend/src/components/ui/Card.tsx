import React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * Container card component with optional title
 * @example
 * <Card title="Detection Stats">
 *   <p>Content goes here</p>
 * </Card>
 */
export const Card: React.FC<CardProps> = ({ title, children, className }) => {
  return (
    <div
      className={cn(
        'bg-[#161b22] rounded-lg border border-[#30363d] overflow-hidden',
        className
      )}
    >
      {title && (
        <div className="px-6 py-4 border-b border-[#30363d]">
          <h3 className="text-lg font-semibold text-[#e6edf3]">{title}</h3>
        </div>
      )}
      <div className={cn(title ? 'p-6' : 'p-6')}>
        {children}
      </div>
    </div>
  );
};
