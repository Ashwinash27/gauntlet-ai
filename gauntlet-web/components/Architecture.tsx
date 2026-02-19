"use client";

import { motion } from "framer-motion";

const LAYERS = [
  { num: "01", name: "Regex Pattern Matching", detail: "51 rules", speed: "~0.1ms", cost: "$0/req" },
  { num: "02", name: "Embedding Similarity", detail: "603 vectors", speed: "~285ms", cost: "~$0.0001/req" },
  { num: "03", name: "LLM Judge (Claude Haiku)", detail: "reasoning", speed: "~1.4s", cost: "~$0.003/req" },
];

const fadeIn = {
  initial: { opacity: 0, y: 8 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-64px" },
  transition: { duration: 0.4, ease: "easeOut" },
};

export default function Architecture() {
  return (
    <motion.section {...fadeIn}>
      <p className="text-xs tracking-[0.2em] uppercase text-[#888888] mb-8">
        How It Works
      </p>

      <div className="border-t border-[#1F1F1F]">
        {LAYERS.map((layer) => (
          <div
            key={layer.num}
            className="border-b border-[#1F1F1F] py-4 flex items-baseline gap-6 font-mono text-sm"
          >
            <span className="text-[#555555] shrink-0">{layer.num}</span>
            <span className="text-[#EDEDED] min-w-[200px]">{layer.name}</span>
            <span className="text-[#888888] min-w-[88px]">{layer.detail}</span>
            <span className="text-[#555555] min-w-[64px] text-right">{layer.speed}</span>
            <span className="text-[#555555] ml-auto">{layer.cost}</span>
          </div>
        ))}
      </div>

      <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-xs font-mono text-[#555555]">
        <span>603 attack vectors</span>
        <span className="text-[#333333]">|</span>
        <span>9,300+ eval samples</span>
        <span className="text-[#333333]">|</span>
        <span>&lt;1.5% false positive rate</span>
        <span className="text-[#333333]">|</span>
        <span>379 tests</span>
      </div>

      <p className="mt-6 text-[#888888] text-sm leading-relaxed max-w-[600px]">
        Each layer acts as a gate. Fast and cheap first. Slow and smart last.
        Most requests never reach Layer 3.
      </p>
    </motion.section>
  );
}
