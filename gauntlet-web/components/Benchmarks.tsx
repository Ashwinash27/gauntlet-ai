"use client";

import { motion } from "framer-motion";

const ROWS = [
  { benchmark: "Internal (known)", config: "L1+2", f1: "98.04%", recall: "100%", fpr: "0.60%", external: false },
  { benchmark: "Internal (holdout)", config: "L1+2", f1: "96.08%", recall: "98%", fpr: "0.60%", external: false },
  { benchmark: "PINT", config: "L1+2+3", f1: "90.82%", recall: "87.25%", fpr: "1.46%", external: true },
];

const HEADERS = ["Benchmark", "Config", "F1", "Recall", "FPR"];

export default function Benchmarks() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-64px" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <h2 className="text-[32px] font-semibold text-[#EDEDED]">
        Benchmarks
      </h2>
      <p className="mt-2 text-[15px] text-[#888888] mb-8">
        Evaluated across internal holdout and external datasets.
      </p>

      <div className="bg-[#111111] border border-[#1E1E1E] rounded-[8px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#0F0F0F]">
                {HEADERS.map((h) => (
                  <th
                    key={h}
                    className="text-left text-[11px] uppercase tracking-[0.1em] text-[#555555] px-5 py-3 font-normal whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const fprValue = parseFloat(row.fpr);
                return (
                  <tr key={row.benchmark} className="border-t border-[#1A1A1A]">
                    <td className="px-5 py-4 text-[14px] font-medium text-[#EDEDED] whitespace-nowrap">
                      {row.benchmark}
                      {row.external && (
                        <span className="ml-2 text-[10px] bg-[#1A1A1A] text-[#666666] rounded px-2 py-0.5 inline-block align-middle">
                          external
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 font-mono text-[14px] text-[#CCCCCC]">
                      {row.config}
                    </td>
                    <td className="px-5 py-4 font-mono text-[14px] text-[#CCCCCC] font-medium">
                      {row.f1}
                    </td>
                    <td className="px-5 py-4 font-mono text-[14px] text-[#CCCCCC]">
                      {row.recall}
                    </td>
                    <td
                      className={`px-5 py-4 font-mono text-[14px] ${
                        fprValue < 2 ? "text-[#22C55E]" : "text-[#CCCCCC]"
                      }`}
                    >
                      {row.fpr}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </motion.section>
  );
}
