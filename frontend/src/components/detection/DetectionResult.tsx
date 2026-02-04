import React from 'react';
import { StatusBadge } from './StatusBadge';
import type { DetectionResult as DetectionResultType } from '@/types';

export interface DetectionResultProps {
  result: DetectionResultType;
  className?: string;
}

/**
 * Terminal-style detection result display
 */
export const DetectionResult: React.FC<DetectionResultProps> = ({
  result,
  className,
}) => {
  return (
    <div className={`terminal-box rounded-lg p-4 bg-black ${className || ''}`}>
      {/* Status */}
      <div className="mb-4">
        <StatusBadge
          isInjection={result.is_injection}
          attackType={result.attack_type}
        />
      </div>

      {/* Layer Results */}
      {result.layers && result.layers.length > 0 && (
        <div className="space-y-1 text-sm mb-4">
          {result.layers.map((layer, index) => (
            <p key={index} className="text-[#00cc00]">
              &gt; Layer {layer.layer} ({layer.name})........{' '}
              <span className={layer.passed ? 'text-[#00ff00]' : 'text-[#ff0000]'}>
                {layer.passed ? 'PASS' : 'THREAT'}
              </span>
              {'  '}
              <span className="text-[#006600]">{layer.latency_ms}ms</span>
            </p>
          ))}
        </div>
      )}

      {/* Stats */}
      <div className="pt-4 border-t border-[rgba(0,255,0,0.2)] space-y-1 text-sm">
        <p className="text-[#00cc00]">
          &gt; CONFIDENCE: <span className="text-[#00ff00]">{result.confidence}%</span>
        </p>
        <p className="text-[#00cc00]">
          &gt; LATENCY: <span className="text-[#006600]">{result.latency_ms}ms</span>
        </p>
      </div>
    </div>
  );
};
