import { useState, useEffect, useRef } from 'react';
import { motion, useInView } from 'framer-motion';

interface CountUpProps {
  end: number;
  start?: number;
  duration?: number;
  delay?: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
  once?: boolean;
}

/**
 * Animates a number counting up from start to end value.
 */
export function CountUp({
  end,
  start = 0,
  duration = 2,
  delay = 0,
  decimals = 0,
  suffix = '',
  prefix = '',
  className = '',
  once = true,
}: CountUpProps) {
  const [count, setCount] = useState(start);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once });
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    if (!isInView || (once && hasAnimated)) return;

    setHasAnimated(true);
    const startTime = Date.now();

    const delayTimeout = setTimeout(() => {
      const animate = () => {
        const now = Date.now();
        const progress = Math.min((now - startTime - delay * 1000) / (duration * 1000), 1);

        if (progress < 0) {
          requestAnimationFrame(animate);
          return;
        }

        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;

        setCount(current);

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          setCount(end);
        }
      };

      requestAnimationFrame(animate);
    }, delay * 1000);

    return () => clearTimeout(delayTimeout);
  }, [isInView, start, end, duration, delay, once, hasAnimated]);

  const formattedCount = count.toFixed(decimals);

  return (
    <motion.span
      ref={ref}
      initial={{ opacity: 0, y: 10 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
      transition={{ duration: 0.3 }}
      className={className}
    >
      {prefix}
      {formattedCount}
      {suffix}
    </motion.span>
  );
}
