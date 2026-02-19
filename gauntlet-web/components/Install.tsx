"use client";

import { useState } from "react";
import { motion } from "framer-motion";

const fadeIn = {
  initial: { opacity: 0, y: 8 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-64px" },
  transition: { duration: 0.4, ease: "easeOut" },
};

export default function Install() {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText("pip install gauntlet-ai");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <motion.section {...fadeIn}>
      <p className="text-xs tracking-[0.2em] uppercase text-[#888888] mb-8">
        Install
      </p>

      <div className="flex items-center gap-4 bg-[#141414] border border-[#1F1F1F] rounded-[4px] px-4 py-3">
        <code className="font-mono text-sm text-[#EDEDED] flex-1">
          pip install gauntlet-ai
        </code>
        <button
          onClick={handleCopy}
          className="text-xs text-[#888888] hover:text-[#EDEDED] transition-colors duration-150 shrink-0"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>

      <p className="mt-4 text-sm text-[#888888]">
        <a
          href="https://github.com/Ashwinash27/gauntlet-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#EDEDED] transition-colors duration-150"
        >
          GitHub
        </a>
        <span className="mx-2">&middot;</span>
        <a
          href="https://pypi.org/project/gauntlet-ai/"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#EDEDED] transition-colors duration-150"
        >
          PyPI
        </a>
      </p>
    </motion.section>
  );
}
