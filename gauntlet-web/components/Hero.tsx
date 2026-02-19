"use client";

import { motion } from "framer-motion";

const fadeIn = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, ease: "easeOut" },
};

export default function Hero() {
  return (
    <motion.section className="text-center" {...fadeIn}>
      <h1 className="text-[72px] font-semibold tracking-tight leading-none">
        Gauntlet AI
      </h1>
      <p className="mt-4 text-lg text-[#888888]">
        Prompt injection detection in three layers.
      </p>
      <hr className="mt-16 border-[#1F1F1F]" />
    </motion.section>
  );
}
