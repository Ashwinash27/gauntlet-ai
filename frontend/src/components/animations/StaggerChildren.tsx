import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import React from 'react';

interface StaggerChildrenProps {
  children: React.ReactNode;
  staggerDelay?: number;
  initialDelay?: number;
  className?: string;
  direction?: 'up' | 'down' | 'left' | 'right';
}

const getItemVariants = (direction: string): Variants => {
  const offset = 20;
  const initial: Record<string, { opacity: number; x?: number; y?: number }> = {
    up: { opacity: 0, y: offset },
    down: { opacity: 0, y: -offset },
    left: { opacity: 0, x: offset },
    right: { opacity: 0, x: -offset },
  };

  return {
    hidden: initial[direction],
    visible: {
      opacity: 1,
      x: 0,
      y: 0,
      transition: {
        duration: 0.4,
        ease: 'easeOut',
      },
    },
  };
};

/**
 * Animates children with staggered delays.
 */
export function StaggerChildren({
  children,
  staggerDelay = 0.1,
  initialDelay = 0,
  className = '',
  direction = 'up',
}: StaggerChildrenProps) {
  const itemVariants = getItemVariants(direction);

  const containerVariantsWithDelay: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delayChildren: initialDelay,
        staggerChildren: staggerDelay,
      },
    },
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariantsWithDelay}
      className={className}
    >
      {React.Children.map(children, (child) => (
        <motion.div variants={itemVariants}>{child}</motion.div>
      ))}
    </motion.div>
  );
}

/**
 * Individual item for manual stagger control.
 */
export function StaggerItem({
  children,
  className = '',
  direction = 'up',
}: {
  children: React.ReactNode;
  className?: string;
  direction?: 'up' | 'down' | 'left' | 'right';
}) {
  const itemVariants = getItemVariants(direction);

  return (
    <motion.div variants={itemVariants} className={className}>
      {children}
    </motion.div>
  );
}
