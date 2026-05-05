import type { TradeGuidance } from "@/lib/types";

function Row({ label, value, highlight }: { label: string; value: string; highlight?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className={`text-sm font-semibold ${highlight ?? "text-gray-900"}`}>{value}</span>
    </div>
  );
}

export function TradeGuidanceCard({ guidance }: { guidance: TradeGuidance }) {
  const bull = guidance.is_bullish;
  const borderColor = bull ? "border-green-200" : "border-red-200";
  const bgColor     = bull ? "bg-green-50"     : "bg-red-50";
  const actionColor = bull ? "text-green-800"  : "text-red-800";
  const badgeBg     = bull ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700";

  const fmt = (v: number) => `$${v.toFixed(2)}`;

  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} p-5`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Trade Guidance</h2>
          <p className={`text-sm font-medium ${actionColor}`}>{guidance.action}</p>
        </div>
        <span className={`text-xs font-semibold px-2 py-1 rounded-full whitespace-nowrap ${badgeBg}`}>
          R/R {guidance.risk_reward}:1
        </span>
      </div>

      {/* Rationale */}
      <p className="text-sm text-gray-600 mb-4 leading-relaxed">{guidance.rationale}</p>

      {/* Levels */}
      <div className="bg-white rounded-lg px-4 py-1 border border-gray-100">
        <Row
          label={bull ? "Entry zone" : "Exit zone"}
          value={
            guidance.entry_low === guidance.entry_high
              ? fmt(guidance.entry_low)
              : `${fmt(guidance.entry_low)} – ${fmt(guidance.entry_high)}`
          }
          highlight="text-gray-900"
        />
        <Row
          label={bull ? "Price target" : "Downside target"}
          value={fmt(guidance.target)}
          highlight={bull ? "text-green-700" : "text-red-700"}
        />
        <Row
          label="Stop loss"
          value={fmt(guidance.stop_loss)}
          highlight="text-red-600"
        />
        <Row
          label="ATR (14)"
          value={fmt(guidance.atr)}
        />
      </div>

      <p className="text-xs text-gray-400 mt-3">
        Not financial advice. Levels are calculated from ATR and EMA indicators.
      </p>
    </div>
  );
}
