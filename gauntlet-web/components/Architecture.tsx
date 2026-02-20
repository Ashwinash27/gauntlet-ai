"use client";

import { Fragment } from "react";
import { motion } from "framer-motion";

const LAYERS = [
  { num: "1", name: "Regex", stat: "51 rules", speed: "~0.1ms", cost: "$0/req" },
  { num: "2", name: "Embeddings", stat: "603 vectors", speed: "~285ms", cost: "~$0.0001/req" },
  { num: "3", name: "LLM Judge", stat: "Claude Haiku", speed: "~1.4s", cost: "~$0.003/req" },
];

export default function Architecture() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-64px" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <h2 className="text-[32px] font-semibold text-[#EDEDED]">
        How it works
      </h2>

      <div className="mt-10 flex flex-col md:flex-row md:items-stretch gap-3">
        {LAYERS.map((layer, i) => (
          <Fragment key={layer.num}>
            {i > 0 && (
              <div className="hidden md:flex items-center justify-center shrink-0">
                <span className="text-[#333333] text-lg">&rarr;</span>
              </div>
            )}
            <div className="flex-1 bg-[#111111] border border-[#1E1E1E] rounded-[8px] p-6 relative overflow-hidden">
              <span className="absolute top-3 right-4 text-[48px] font-bold text-[#1A1A1A] leading-none select-none pointer-events-none">
                {layer.num}
              </span>
              <p className="text-[18px] font-medium text-[#EDEDED] relative">
                {layer.name}
              </p>
              <p className="mt-1 text-[14px] text-[#888888] relative">
                {layer.stat}
              </p>
              <p className="mt-2 text-[12px] font-mono text-[#555555] relative">
                {layer.speed} &middot; {layer.cost}
              </p>
            </div>
          </Fragment>
        ))}
      </div>

      <p className="mt-8 text-[15px] text-[#777777]">
        Fast and free first. Slow and smart last. Most requests never reach Layer 3.
      </p>
    </motion.section>
  );
}
