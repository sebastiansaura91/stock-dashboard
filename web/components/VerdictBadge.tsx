import type { Verdict } from "@/lib/types";

const STYLES: Record<Verdict, string> = {
  "Strong BUY":  "bg-green-100 text-green-800 border-green-200",
  "BUY":         "bg-green-50  text-green-700 border-green-100",
  "HOLD":        "bg-amber-50  text-amber-700 border-amber-100",
  "SELL":        "bg-red-50    text-red-700   border-red-100",
  "Strong SELL": "bg-red-100   text-red-800   border-red-200",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${STYLES[verdict] ?? STYLES["HOLD"]}`}>
      {verdict}
    </span>
  );
}
