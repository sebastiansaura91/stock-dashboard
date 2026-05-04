import type { ChartPattern } from "@/lib/types";

const DIRECTION_STYLES = {
  bullish: "bg-green-50 text-green-700 border-green-100",
  bearish: "bg-red-50 text-red-700 border-red-100",
  neutral: "bg-gray-50 text-gray-600 border-gray-100",
};

const RELIABILITY_STYLES = {
  High:   "text-indigo-600 font-medium",
  Medium: "text-gray-500",
};

export function PatternCard({ pattern }: { pattern: ChartPattern }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-gray-900">{pattern.name}</div>
          <div className="text-sm text-gray-600 mt-1">{pattern.meaning}</div>
          <div className={`text-xs mt-2 ${RELIABILITY_STYLES[pattern.reliability] ?? "text-gray-500"}`}>
            {pattern.reliability} reliability · detected {pattern.detected_at}
          </div>
        </div>
        <span className={`shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${DIRECTION_STYLES[pattern.direction] ?? DIRECTION_STYLES.neutral}`}>
          {pattern.direction}
        </span>
      </div>
    </div>
  );
}
