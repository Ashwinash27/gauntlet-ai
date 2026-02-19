"use client";

import { motion } from "framer-motion";

const ROWS = [
  { benchmark: "Internal (known)", config: "L1+2", f1: "98.04%", recall: "100%", fpr: "0.60%" },
  { benchmark: "Internal (holdout)", config: "L1+2", f1: "96.08%", recall: "98%", fpr: "0.60%" },
  { benchmark: "PINT External", config: "L1+2+3", f1: "90.82%", recall: "87.25%", fpr: "1.46%" },
];

const HEADERS = ["Benchmark", "Config", "F1", "Recall", "FPR"];

const fadeIn = {
  initial: { opacity: 0, y: 8 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-64px" },
  transition: { duration: 0.4, ease: "easeOut" },
};

export default function Benchmarks() {
  return (
    <motion.section {...fadeIn}>
      <p className="text-xs tracking-[0.2em] uppercase text-[#888888] mb-8">
        Benchmarks
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-[#1F1F1F]">
              {HEADERS.map((h) => (
                <th
                  key={h}
                  className="text-left text-[#888888] font-normal py-3 pr-6 first:pl-0"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.benchmark} className="border-b border-[#1F1F1F]">
                <td className="py-3 pr-6 text-[#EDEDED]">{row.benchmark}</td>
                <td className="py-3 pr-6 font-mono text-[#888888]">{row.config}</td>
                <td className="py-3 pr-6 font-mono text-[#EDEDED]">{row.f1}</td>
                <td className="py-3 pr-6 font-mono text-[#EDEDED]">{row.recall}</td>
                <td className="py-3 pr-6 font-mono text-[#EDEDED]">{row.fpr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-6 text-[#888888] text-sm">
        Evaluated on 9,300+ samples including deepset/prompt-injections external benchmark. Layer 1 recall improved 5.4x after targeted regex expansion.
      </p>
    </motion.section>
  );
}
