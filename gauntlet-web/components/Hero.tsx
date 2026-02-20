"use client";

import { motion } from "framer-motion";

const stats = [
  { value: "603", label: "vectors" },
  { value: "9,300+", label: "samples" },
  { value: "91%", label: "F1" },
  { value: "<1.5%", label: "FPR" },
];

export default function Hero() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <h1 className="text-[80px] font-bold tracking-[-0.03em] leading-none text-[#EDEDED]">
        Gauntlet AI
      </h1>

      <p className="mt-4 text-[20px] text-[#888888] max-w-[400px]">
        Three-layer defense against prompt injection.
      </p>

      <div className="mt-5 flex items-center gap-4 text-[14px]">
        <span className="text-[#888888]">by Ashwin</span>
        <span className="w-px h-3 bg-[#333333]" />
        <a
          href="https://www.linkedin.com/in/ashwin-shanmugasundaram/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#888888] hover:text-[#EDEDED] transition-colors duration-150 flex items-center gap-1.5"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
          <span>LinkedIn</span>
        </a>
        <a
          href="https://github.com/Ashwinash27/gauntlet-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#888888] hover:text-[#EDEDED] transition-colors duration-150 flex items-center gap-1.5"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          <span>GitHub</span>
        </a>
      </div>

      <div className="mt-8 flex items-center font-mono text-[13px]">
        {stats.map((stat, i) => (
          <div key={stat.label} className="flex items-center">
            {i > 0 && <span className="mx-4 w-px h-3 bg-[#333333]" />}
            <span>
              <span className="text-[#999999]">{stat.value}</span>
              <span className="text-[#555555]"> {stat.label}</span>
            </span>
          </div>
        ))}
      </div>

      <a
        href="#playground"
        className="mt-10 inline-block text-[#555555] hover:text-[#888888] transition-colors duration-150"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M4 6l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </a>
    </motion.section>
  );
}
