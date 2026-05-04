import { api } from "@/lib/api";
import { StockTable } from "@/components/StockTable";
import { ScreenerFilters } from "./ScreenerFilters";
import type { ScreenerResult } from "@/lib/types";

export const revalidate = 3600; // screener cache refreshes hourly

interface Props {
  searchParams: { min_score?: string; verdict?: string; sector?: string };
}

export default async function ScreenerPage({ searchParams }: Props) {
  const minScore = Number(searchParams.min_score ?? 0);
  const verdict = searchParams.verdict ?? "";
  const sector = searchParams.sector ?? "";

  let results: ScreenerResult[] = [];
  try {
    results = await api.screener.query({ min_score: minScore, verdict, sector, limit: 100 });
  } catch {
    // Backend not reachable
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">S&P 500 Screener</h1>
        <p className="text-sm text-gray-500 mt-1">
          {results.length} result{results.length !== 1 ? "s" : ""} · only cached tickers shown
        </p>
      </div>

      <ScreenerFilters initialMinScore={minScore} initialVerdict={verdict} initialSector={sector} />

      <StockTable rows={results} />
    </div>
  );
}
