"use client";

import { useState } from "react";
import Link from "next/link";
import type { WatchlistItem, ScreenerResult } from "@/lib/types";
import { VerdictBadge } from "./VerdictBadge";

type Row = WatchlistItem | ScreenerResult;

type SortKey = "ticker" | "final_score" | "price";

function sortRows(rows: Row[], key: SortKey, asc: boolean): Row[] {
  return [...rows].sort((a, b) => {
    const va = a[key] ?? -Infinity;
    const vb = b[key] ?? -Infinity;
    if (va < vb) return asc ? -1 : 1;
    if (va > vb) return asc ? 1 : -1;
    return 0;
  });
}

interface Props {
  rows: Row[];
  onRemove?: (ticker: string) => void;
  onAdd?: (ticker: string) => void;
  addLabel?: string;
}

export function StockTable({ rows, onRemove, onAdd, addLabel = "Add" }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("final_score");
  const [asc, setAsc] = useState(false);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setAsc(!asc);
    else { setSortKey(key); setAsc(false); }
  }

  const sorted = sortRows(rows, sortKey, asc);
  const arrow = (key: SortKey) => sortKey === key ? (asc ? " ↑" : " ↓") : "";

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th onClick={() => toggleSort("ticker")} className="px-4 py-3 text-left font-semibold text-gray-600 cursor-pointer select-none">
              Ticker{arrow("ticker")}
            </th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Company</th>
            <th onClick={() => toggleSort("price")} className="px-4 py-3 text-right font-semibold text-gray-600 cursor-pointer select-none">
              Price{arrow("price")}
            </th>
            <th onClick={() => toggleSort("final_score")} className="px-4 py-3 text-right font-semibold text-gray-600 cursor-pointer select-none">
              Score{arrow("final_score")}
            </th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Verdict</th>
            {(onRemove || onAdd) && <th className="px-4 py-3" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {sorted.map((row) => (
            <tr key={row.ticker} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-mono font-semibold text-indigo-600">
                <Link href={`/stock/${row.ticker}`} className="hover:underline">
                  {row.ticker}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-700">{row.company}</td>
              <td className="px-4 py-3 text-right text-gray-900">
                {row.price != null ? `$${row.price.toFixed(2)}` : "—"}
              </td>
              <td className="px-4 py-3 text-right font-semibold text-gray-900">
                {row.final_score ?? "—"}
              </td>
              <td className="px-4 py-3">
                <VerdictBadge verdict={row.verdict} />
              </td>
              {(onRemove || onAdd) && (
                <td className="px-4 py-3 text-right">
                  {onRemove && (
                    <button onClick={() => onRemove(row.ticker)} className="text-xs text-gray-400 hover:text-red-500 transition-colors">
                      Remove
                    </button>
                  )}
                  {onAdd && (
                    <button onClick={() => onAdd(row.ticker)} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors">
                      {addLabel}
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-8 text-center text-gray-400">No results</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
