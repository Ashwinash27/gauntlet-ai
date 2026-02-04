import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface GlitchTextProps {
  text: string;
  className?: string;
  trigger?: boolean;
  intensity?: 'low' | 'medium' | 'high';
  glitchOnHover?: boolean;
}

/**
 * Displays text with a glitch effect that can be triggered or activated on hover.
 */
export function GlitchText({
  text,
  className = '',
  trigger = false,
  intensity = 'medium',
  glitchOnHover = false,
}: GlitchTextProps) {
  const [isGlitching, setIsGlitching] = useState(false);
  const [displayText, setDisplayText] = useState(text);

  const glitchChars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`0123456789';

  const intensityConfig = {
    low: { iterations: 3, interval: 50 },
    medium: { iterations: 6, interval: 40 },
    high: { iterations: 10, interval: 30 },
  };

  useEffect(() => {
    if (!trigger && !isGlitching) return;

    const { iterations, interval } = intensityConfig[intensity];
    let count = 0;

    const glitchInterval = setInterval(() => {
      if (count < iterations) {
        const glitchedText = text
          .split('')
          .map((char) => {
            if (char === ' ') return ' ';
            return Math.random() > 0.7
              ? glitchChars[Math.floor(Math.random() * glitchChars.length)]
              : char;
          })
          .join('');
        setDisplayText(glitchedText);
        count++;
      } else {
        setDisplayText(text);
        setIsGlitching(false);
        clearInterval(glitchInterval);
      }
    }, interval);

    return () => clearInterval(glitchInterval);
  }, [trigger, text, intensity]);

  const handleMouseEnter = () => {
    if (glitchOnHover) {
      setIsGlitching(true);
    }
  };

  return (
    <motion.span
      className={`relative inline-block overflow-hidden ${className}`}
      onMouseEnter={handleMouseEnter}
      animate={
        isGlitching || trigger
          ? {
              x: [0, -1, 1, 0],
              filter: [
                'hue-rotate(0deg)',
                'hue-rotate(90deg)',
                'hue-rotate(180deg)',
                'hue-rotate(0deg)',
              ],
            }
          : {}
      }
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      {/* Main text */}
      <span className="relative z-10">{displayText}</span>

      {/* Glitch layers */}
      {(isGlitching || trigger) && (
        <>
          <motion.span
            className="absolute inset-0 text-neon-cyan opacity-50"
            style={{ clipPath: 'polygon(0 0, 100% 0, 100% 45%, 0 45%)' }}
            animate={{ x: [-1, 1, -1] }}
            transition={{ duration: 0.15, repeat: 2 }}
          >
            {displayText}
          </motion.span>
          <motion.span
            className="absolute inset-0 text-neon-magenta opacity-50"
            style={{ clipPath: 'polygon(0 55%, 100% 55%, 100% 100%, 0 100%)' }}
            animate={{ x: [1, -1, 1] }}
            transition={{ duration: 0.15, repeat: 2 }}
          >
            {displayText}
          </motion.span>
        </>
      )}
    </motion.span>
  );
}
