"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { StockTable } from "@/components/StockTable";
import { AddTicker } from "./AddTicker";
import type { WatchlistItem } from "@/lib/types";

const REFRESH_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes

export function WatchlistClient({ initialItems }: { initialItems: WatchlistItem[] }) {
  const [items, setItems] = useState<WatchlistItem[]>(initialItems);

  const refresh = useCallback(async () => {
    try {
      const fresh = await api.watchlist.list();
      setItems(fresh);
    } catch { /* silent — keep showing stale data */ }
  }, []);

  // Auto-refresh every 15 minutes
  useEffect(() => {
    const id = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  async function handleRemove(ticker: string) {
    try {
      await api.watchlist.remove(ticker);
      setItems((prev) => prev.filter((i) => i.ticker !== ticker));
    } catch {
      alert(`Failed to remove ${ticker}`);
    }
  }

  function handleAdd(_ticker: string) {
    // Trigger a refresh so the newly added ticker's data appears
    refresh();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Watchlist</h1>
          <p className="text-sm text-gray-500 mt-1">Auto-refreshes every 15 minutes</p>
        </div>
        <AddTicker onAdd={handleAdd} />
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-4xl mb-3">📋</div>
          <div>No tickers yet — add one above</div>
        </div>
      ) : (
        <StockTable rows={items} onRemove={handleRemove} />
      )}
    </div>
  );
}
