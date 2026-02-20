"use client";

import { useState } from "react";
import { motion } from "framer-motion";

export default function Install() {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText("pip install gauntlet-ai");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-64px" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <h2 className="text-[32px] font-semibold text-[#EDEDED]">
        Get started
      </h2>

      <div className="mt-8 bg-[#111111] border border-[#1E1E1E] rounded-[8px] px-5 py-4 flex items-center">
        <code className="font-mono text-[15px] text-[#CCCCCC] flex-1">
          pip install gauntlet-ai
        </code>
        <button
          onClick={handleCopy}
          className="text-[13px] font-mono text-[#555555] hover:text-[#888888] transition-colors duration-150 shrink-0"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      <p className="mt-4 text-[14px] text-[#555555]">
        <a
          href="https://github.com/Ashwinash27/gauntlet-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#888888] transition-colors duration-150"
        >
          GitHub
        </a>
        <span className="mx-2">&middot;</span>
        <a
          href="https://pypi.org/project/gauntlet-ai/"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#888888] transition-colors duration-150"
        >
          PyPI
        </a>
      </p>
    </motion.section>
  );
}
