import { motion } from 'framer-motion';

interface ScanLinesProps {
  className?: string;
  opacity?: number;
  animated?: boolean;
}

/**
 * CRT-style scan lines overlay with optional moving scan line.
 */
export function ScanLines({ className = '', opacity = 0.4, animated = true }: ScanLinesProps) {
  return (
    <div className={`fixed inset-0 pointer-events-none ${className}`} style={{ zIndex: 100 }}>
      {/* Static scan lines */}
      <div
        className="absolute inset-0"
        style={{
          background: `repeating-linear-gradient(
            0deg,
            rgba(0, 0, 0, 0.15),
            rgba(0, 0, 0, 0.15) 1px,
            transparent 1px,
            transparent 2px
          )`,
          opacity,
        }}
      />

      {/* Moving scan line */}
      {animated && (
        <motion.div
          className="absolute inset-x-0 h-1"
          style={{
            background: `linear-gradient(
              180deg,
              transparent,
              rgba(0, 240, 255, 0.1),
              rgba(0, 240, 255, 0.2),
              rgba(0, 240, 255, 0.1),
              transparent
            )`,
          }}
          initial={{ top: '-1%' }}
          animate={{ top: '101%' }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'linear',
          }}
        />
      )}
    </div>
  );
}
