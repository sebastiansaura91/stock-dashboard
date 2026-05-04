import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { VerdictBadge } from "@/components/VerdictBadge";
import { ScoreBar } from "@/components/ScoreBar";
import { DriverList } from "@/components/DriverList";
import { PatternCard } from "@/components/PatternCard";
import { PriceChart } from "@/components/PriceChart";
import type { StockDetail } from "@/lib/types";

export const revalidate = 900;

function fmt(v: number | null, suffix = "", decimals = 2): string {
  if (v === null) return "N/A";
  return `${(v * (suffix === "%" ? 100 : 1)).toFixed(decimals)}${suffix}`;
}

export default async function StockPage({ params }: { params: { ticker: string } }) {
  let stock!: StockDetail;
  try {
    stock = await api.stock.get(params.ticker.toUpperCase());
  } catch {
    notFound();
  }

  const f = stock.fundamentals;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">{stock.ticker}</h1>
            <VerdictBadge verdict={stock.verdict} />
          </div>
          <div className="text-gray-500 mt-1">{stock.company}</div>
          {stock.price != null && (
            <div className="text-2xl font-semibold text-gray-900 mt-2">
              ${stock.price.toFixed(2)}
            </div>
          )}
        </div>
        {stock.final_score != null && (
          <div className="text-right">
            <div className="text-4xl font-bold text-gray-900">{stock.final_score}</div>
            <div className="text-xs text-gray-400 mt-1">Final Score</div>
          </div>
        )}
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Technical", score: stock.technical_score },
          { label: "Fundamental", score: stock.fundamental_score },
          { label: "Sentiment", score: stock.sentiment_score },
        ].map(({ label, score }) => (
          <div key={label} className="border border-gray-200 rounded-xl p-4 bg-white">
            <ScoreBar score={score} label={label} />
          </div>
        ))}
      </div>

      {/* Price chart */}
      {stock.ohlcv.dates.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Price (6 months)</h2>
          <PriceChart ohlcv={stock.ohlcv} />
        </div>
      )}

      {/* Chart patterns */}
      {stock.patterns.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Chart Patterns Detected
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {stock.patterns.map((p, i) => (
              <PatternCard key={i} pattern={p} />
            ))}
          </div>
        </div>
      )}

      {/* Driver breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <DriverList title="Technical Signals" drivers={stock.technical_drivers} />
        <DriverList title="Fundamental Signals" drivers={stock.fundamental_drivers} />
        <DriverList title="Sentiment Signals" drivers={stock.sentiment_drivers} />
      </div>

      {/* Key ratios */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Key Ratios</h2>
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="min-w-full text-sm divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["Metric", "Value"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {[
                ["P/E Ratio", fmt(f.pe_ratio, "x", 1)],
                ["EV/EBITDA", fmt(f.ev_ebitda, "x", 1)],
                ["Revenue Growth (YoY)", fmt(f.revenue_growth_yoy, "%", 1)],
                ["Gross Margin", fmt(f.gross_margin, "%", 1)],
                ["Operating Margin", fmt(f.operating_margin, "%", 1)],
                ["Debt / Equity", fmt(f.debt_equity, "x", 2)],
                ["Sector", f.sector ?? "N/A"],
              ].map(([label, value]) => (
                <tr key={label} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-600">{label}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {stock.fetched_at && (
        <p className="text-xs text-gray-400">
          Last updated: {new Date(stock.fetched_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
