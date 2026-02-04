import { motion } from 'framer-motion';

interface GridBackgroundProps {
  className?: string;
  perspective?: boolean;
  opacity?: number;
}

/**
 * Animated grid background with optional perspective floor effect.
 */
export function GridBackground({
  className = '',
  perspective = false,
  opacity = 0.03,
}: GridBackgroundProps) {
  if (perspective) {
    return (
      <div className={`absolute inset-0 overflow-hidden ${className}`}>
        {/* Perspective floor grid */}
        <div
          className="absolute inset-x-0 bottom-0 h-[60vh]"
          style={{
            background: `
              linear-gradient(rgba(0, 240, 255, ${opacity * 3}) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0, 240, 255, ${opacity * 3}) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
            transform: 'perspective(500px) rotateX(60deg)',
            transformOrigin: 'center top',
            maskImage: 'linear-gradient(to bottom, transparent, black 20%, black 80%, transparent)',
            WebkitMaskImage:
              'linear-gradient(to bottom, transparent, black 20%, black 80%, transparent)',
          }}
        />

        {/* Horizon glow */}
        <div
          className="absolute inset-x-0 top-1/2 h-px"
          style={{
            background: `linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.3), transparent)`,
            boxShadow: '0 0 30px rgba(0, 240, 255, 0.2)',
          }}
        />
      </div>
    );
  }

  return (
    <motion.div
      className={`absolute inset-0 ${className}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
      style={{
        background: `
          linear-gradient(rgba(0, 240, 255, ${opacity}) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 240, 255, ${opacity}) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px',
      }}
    />
  );
}
