import React from 'react';

export interface StatusBadgeProps {
  isInjection: boolean;
  attackType?: string;
  className?: string;
}

/**
 * Terminal-style status badge for detection results
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  isInjection,
  attackType,
  className,
}) => {
  return (
    <div className={`text-center ${className || ''}`}>
      <div
        className={`inline-block px-4 py-2 text-lg font-bold ${
          isInjection
            ? 'text-[#ff0000] bg-[rgba(255,0,0,0.2)] border border-[#ff0000]'
            : 'text-[#00ff00] bg-[rgba(0,255,0,0.2)] border border-[#00ff00]'
        }`}
      >
        {isInjection ? '██ INJECTION DETECTED ██' : '✓ SAFE'}
      </div>
      {attackType && (
        <p className="mt-2 text-sm text-[#ffff00]">
          Type: {attackType}
        </p>
      )}
    </div>
  );
};
