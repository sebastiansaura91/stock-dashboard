import type { WatchlistItem, StockDetail, ScreenerResult } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API DELETE ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  watchlist: {
    list: () => get<WatchlistItem[]>("/api/watchlist"),
    add: (ticker: string) => post<{ ticker: string; status: string }>("/api/watchlist", { ticker }),
    remove: (ticker: string) => del<{ ticker: string; status: string }>(`/api/watchlist/${ticker}`),
  },
  stock: {
    get: (ticker: string) => get<StockDetail>(`/api/stock/${ticker}`),
  },
  screener: {
    query: (params: { min_score?: number; verdict?: string; sector?: string; limit?: number }) => {
      const qs = new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== "")
          .map(([k, v]) => [k, String(v)])
      ).toString();
      return get<ScreenerResult[]>(`/api/screener${qs ? `?${qs}` : ""}`);
    },
  },
};
