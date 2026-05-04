"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Verdict } from "@/lib/types";

const VERDICTS: (Verdict | "")[] = ["", "Strong BUY", "BUY", "HOLD", "SELL", "Strong SELL"];

const SECTORS = [
  "",
  "Communication Services",
  "Consumer Discretionary",
  "Consumer Staples",
  "Energy",
  "Financials",
  "Health Care",
  "Industrials",
  "Information Technology",
  "Materials",
  "Real Estate",
  "Utilities",
];

export function ScreenerFilters({
  initialMinScore,
  initialVerdict,
  initialSector,
}: {
  initialMinScore: number;
  initialVerdict: string;
  initialSector: string;
}) {
  const [minScore, setMinScore] = useState(initialMinScore);
  const [verdict, setVerdict] = useState(initialVerdict);
  const [sector, setSector] = useState(initialSector);
  const router = useRouter();

  function applyFilters() {
    const qs = new URLSearchParams();
    if (minScore > 0) qs.set("min_score", String(minScore));
    if (verdict) qs.set("verdict", verdict);
    if (sector) qs.set("sector", sector);
    router.push(`/screener?${qs.toString()}`);
  }

  return (
    <div className="flex flex-wrap items-end gap-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
      <div>
        <label className="block text-xs text-gray-500 mb-1">Min Score: {minScore}</label>
        <input
          type="range"
          min={0}
          max={100}
          value={minScore}
          onChange={(e) => setMinScore(Number(e.target.value))}
          className="w-40 accent-indigo-600"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Verdict</label>
        <select
          value={verdict}
          onChange={(e) => setVerdict(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {VERDICTS.map((v) => (
            <option key={v} value={v}>{v || "Any verdict"}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Sector</label>
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {SECTORS.map((s) => (
            <option key={s} value={s}>{s || "Any sector"}</option>
          ))}
        </select>
      </div>
      <button
        onClick={applyFilters}
        className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
      >
        Apply
      </button>
    </div>
  );
}
