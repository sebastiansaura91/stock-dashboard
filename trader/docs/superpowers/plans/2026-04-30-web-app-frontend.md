# Stock Dashboard — Web App Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean, minimal Next.js web app with three pages (Watchlist, Stock Detail, Screener) that consumes the FastAPI backend.

**Architecture:** Next.js 14 App Router in `web/` directory at the repo root. Tailwind CSS for styling. TradingView Lightweight Charts for the candlestick chart. All API calls go through `web/lib/api.ts`. Each page is a React Server Component that fetches data; interactive elements (chart, add/remove ticker) are Client Components.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS 3, lightweight-charts 4.x, Node.js 18+

**Prerequisite:** Backend deployed to Railway. Set `NEXT_PUBLIC_API_URL` to the Railway URL before starting.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `web/package.json` | Create | Dependencies + scripts |
| `web/tsconfig.json` | Create | TypeScript config |
| `web/next.config.ts` | Create | Next.js config (API URL) |
| `web/tailwind.config.ts` | Create | Tailwind config + custom colours |
| `web/postcss.config.js` | Create | PostCSS for Tailwind |
| `web/app/layout.tsx` | Create | Root layout — nav + font |
| `web/app/page.tsx` | Create | Root redirect → /watchlist |
| `web/app/globals.css` | Create | Tailwind base styles |
| `web/lib/types.ts` | Create | Shared TypeScript types |
| `web/lib/api.ts` | Create | All fetch calls to FastAPI |
| `web/components/VerdictBadge.tsx` | Create | Coloured pill: Strong BUY → Strong SELL |
| `web/components/ScoreBar.tsx` | Create | 0–100 progress bar with colour gradient |
| `web/components/DriverList.tsx` | Create | Bulleted driver text list |
| `web/components/PatternCard.tsx` | Create | Pattern name + explanation + direction badge |
| `web/components/StockTable.tsx` | Create | Sortable table (watchlist + screener) |
| `web/components/PriceChart.tsx` | Create | Candlestick + volume (Lightweight Charts) |
| `web/app/watchlist/page.tsx` | Create | Watchlist page (SSR initial load) |
| `web/app/watchlist/AddTicker.tsx` | Create | Client component: add-ticker input |
| `web/app/watchlist/WatchlistClient.tsx` | Create | Client component: remove + 15-min auto-refresh |
| `web/app/stock/[ticker]/page.tsx` | Create | Stock detail page |
| `web/app/screener/page.tsx` | Create | Screener page with filter controls |
| `web/app/screener/ScreenerFilters.tsx` | Create | Client component: filter controls (score, verdict, sector) |
| `web/vercel.json` | Create | Vercel deployment config |

---

## Task 1: Next.js Scaffold

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/tailwind.config.ts`
- Create: `web/postcss.config.js`
- Create: `web/app/globals.css`
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`

- [ ] **Step 1: Create web/ directory and package.json**

Create `web/package.json`:

```json
{
  "name": "stock-dashboard",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.3",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "lightweight-charts": "^4.1.3"
  },
  "devDependencies": {
    "@types/node": "^20.12.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.3",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create next.config.ts**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
```

- [ ] **Step 4: Create Tailwind config**

`web/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: "#6366f1",   // indigo-500
      },
    },
  },
  plugins: [],
};

export default config;
```

`web/postcss.config.js`:

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 5: Create global CSS + root layout**

`web/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-white text-gray-900 antialiased;
}
```

`web/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock Dashboard",
  description: "Technical, fundamental, and sentiment analysis for equities",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <nav className="border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-8">
          <span className="font-semibold text-gray-900 text-lg">📈 StockDash</span>
          <a href="/watchlist" className="text-sm text-gray-600 hover:text-gray-900">Watchlist</a>
          <a href="/screener" className="text-sm text-gray-600 hover:text-gray-900">Screener</a>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
```

`web/app/page.tsx`:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/watchlist");
}
```

- [ ] **Step 6: Install dependencies and confirm build**

```bash
cd web
npm install
npm run build
```

Expected: build completes with no TypeScript errors. (3 pages, 0 warnings)

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "feat: Next.js scaffold with Tailwind, layout, and root redirect"
```

---

## Task 2: Types + API Client

**Files:**
- Create: `web/lib/types.ts`
- Create: `web/lib/api.ts`

- [ ] **Step 1: Create shared TypeScript types**

`web/lib/types.ts`:

```typescript
export type Verdict = "Strong BUY" | "BUY" | "HOLD" | "SELL" | "Strong SELL";

export interface WatchlistItem {
  ticker: string;
  company: string;
  price: number | null;
  final_score: number | null;
  verdict: Verdict;
  updated_at: string | null;
}

export interface ChartPattern {
  name: string;
  detected_at: string;
  meaning: string;
  reliability: "High" | "Medium";
  direction: "bullish" | "bearish" | "neutral";
}

export interface StockDetail {
  ticker: string;
  company: string;
  price: number | null;
  technical_score: number | null;
  fundamental_score: number | null;
  sentiment_score: number | null;
  final_score: number | null;
  verdict: Verdict;
  ohlcv: {
    dates: string[];
    open: number[];
    high: number[];
    low: number[];
    close: number[];
    volume: number[];
  };
  patterns: ChartPattern[];
  technical_drivers: string[];
  fundamental_drivers: string[];
  sentiment_drivers: string[];
  fundamentals: {
    pe_ratio: number | null;
    ev_ebitda: number | null;
    revenue_growth_yoy: number | null;
    gross_margin: number | null;
    operating_margin: number | null;
    debt_equity: number | null;
    sector: string | null;
    company_name: string | null;
  };
  fetched_at: string | null;
}

export interface ScreenerResult {
  ticker: string;
  company: string;
  sector: string;
  price: number | null;
  final_score: number | null;
  verdict: Verdict;
}
```

- [ ] **Step 2: Create API client**

`web/lib/api.ts`:

```typescript
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

import type { WatchlistItem, StockDetail, ScreenerResult } from "./types";

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
```

- [ ] **Step 3: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add web/lib/
git commit -m "feat: TypeScript types + API client for all endpoints"
```

---

## Task 3: VerdictBadge, ScoreBar, DriverList, PatternCard

**Files:**
- Create: `web/components/VerdictBadge.tsx`
- Create: `web/components/ScoreBar.tsx`
- Create: `web/components/DriverList.tsx`
- Create: `web/components/PatternCard.tsx`

- [ ] **Step 1: VerdictBadge**

`web/components/VerdictBadge.tsx`:

```tsx
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
```

- [ ] **Step 2: ScoreBar**

`web/components/ScoreBar.tsx`:

```tsx
function scoreColour(score: number): string {
  if (score >= 75) return "bg-green-500";
  if (score >= 60) return "bg-green-400";
  if (score >= 45) return "bg-amber-400";
  if (score >= 30) return "bg-red-400";
  return "bg-red-600";
}

export function ScoreBar({ score, label }: { score: number | null; label: string }) {
  if (score === null) {
    return (
      <div className="text-center">
        <div className="text-2xl font-bold text-gray-400">N/A</div>
        <div className="text-xs text-gray-400 mt-1">{label}</div>
      </div>
    );
  }
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-2xl font-bold text-gray-900">{score}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${scoreColour(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: DriverList (collapsible)**

`web/components/DriverList.tsx`:

```tsx
export function DriverList({ drivers, title }: { drivers: string[]; title: string }) {
  if (!drivers.length) return null;
  return (
    <details open>
      <summary className="cursor-pointer text-sm font-semibold text-gray-700 mb-2 select-none">
        {title}
      </summary>
      <ul className="space-y-1 mt-2">
        {drivers.map((d, i) => (
          <li key={i} className="text-sm text-gray-600 flex gap-2">
            <span className="text-gray-300 mt-0.5">•</span>
            <span>{d}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
```

The `<details open>` element is native HTML — no `"use client"` needed. The `open` attribute means the list starts expanded; users can click the title to collapse it.

- [ ] **Step 4: PatternCard**

`web/components/PatternCard.tsx`:

```tsx
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
```

- [ ] **Step 5: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add web/components/VerdictBadge.tsx web/components/ScoreBar.tsx web/components/DriverList.tsx web/components/PatternCard.tsx
git commit -m "feat: VerdictBadge, ScoreBar, DriverList, PatternCard components"
```

---

## Task 4: StockTable Component

**Files:**
- Create: `web/components/StockTable.tsx`

- [ ] **Step 1: Implement StockTable**

`web/components/StockTable.tsx`:

```tsx
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
              {onRemove && (
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onRemove(row.ticker)} className="text-xs text-gray-400 hover:text-red-500 transition-colors">
                    Remove
                  </button>
                </td>
              )}
              {onAdd && (
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onAdd(row.ticker)} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors">
                    {addLabel}
                  </button>
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
```

- [ ] **Step 2: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add web/components/StockTable.tsx
git commit -m "feat: sortable StockTable component with remove/add actions"
```

---

## Task 5: PriceChart Component

**Context:** Lightweight Charts requires a DOM element and browser APIs — it must be a Client Component. Use `useEffect` to initialise the chart after mount. Render candlestick series + volume histogram.

**Files:**
- Create: `web/components/PriceChart.tsx`

- [ ] **Step 1: Implement PriceChart**

`web/components/PriceChart.tsx`:

```tsx
"use client";

import { useEffect, useRef } from "react";

interface OHLCVData {
  dates: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
}

export function PriceChart({ ohlcv }: { ohlcv: OHLCVData }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !ohlcv.dates.length) return;

    let chart: ReturnType<typeof import("lightweight-charts")["createChart"]> | null = null;

    import("lightweight-charts").then(({ createChart, CandlestickSeries, HistogramSeries }) => {
      if (!containerRef.current) return;

      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 320,
        layout: { background: { color: "#ffffff" }, textColor: "#374151" },
        grid: { vertLines: { color: "#f3f4f6" }, horzLines: { color: "#f3f4f6" } },
        rightPriceScale: { borderColor: "#e5e7eb" },
        timeScale: { borderColor: "#e5e7eb", timeVisible: true },
      });

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderUpColor: "#22c55e",
        borderDownColor: "#ef4444",
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: "#93c5fd",
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });

      chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

      const candleData = ohlcv.dates.map((d, i) => ({
        time: d as import("lightweight-charts").Time,
        open: ohlcv.open[i],
        high: ohlcv.high[i],
        low: ohlcv.low[i],
        close: ohlcv.close[i],
      }));

      const volumeData = ohlcv.dates.map((d, i) => ({
        time: d as import("lightweight-charts").Time,
        value: ohlcv.volume[i],
        color: ohlcv.close[i] >= ohlcv.open[i] ? "#bbf7d0" : "#fecaca",
      }));

      candleSeries.setData(candleData);
      volumeSeries.setData(volumeData);
      chart.timeScale().fitContent();

      // Resize observer
      const ro = new ResizeObserver(() => {
        if (containerRef.current && chart) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
      ro.observe(containerRef.current);

      return () => {
        ro.disconnect();
        chart?.remove();
      };
    });

    return () => { chart?.remove(); };
  }, [ohlcv]);

  return (
    <div
      ref={containerRef}
      className="w-full rounded-xl border border-gray-200 overflow-hidden"
      style={{ height: 320 }}
    />
  );
}
```

- [ ] **Step 2: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add web/components/PriceChart.tsx
git commit -m "feat: PriceChart component — candlestick + volume (Lightweight Charts)"
```

---

## Task 6: Watchlist Page

**Files:**
- Create: `web/app/watchlist/AddTicker.tsx`
- Create: `web/app/watchlist/WatchlistClient.tsx`
- Create: `web/app/watchlist/page.tsx`

- [ ] **Step 1: AddTicker client component**

`web/app/watchlist/AddTicker.tsx`:

```tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function AddTicker({ onAdd }: { onAdd: (ticker: string) => void }) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    try {
      await api.watchlist.add(ticker);
      setValue("");
      onAdd(ticker);
    } catch {
      alert(`Failed to add ${ticker}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleAdd} className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value.toUpperCase())}
        placeholder="Add ticker (e.g. TSLA)"
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "Adding…" : "Add"}
      </button>
    </form>
  );
}
```

- [ ] **Step 2: WatchlistClient — handles remove + 15-min auto-refresh**

`web/app/watchlist/WatchlistClient.tsx`:

```tsx
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
```

- [ ] **Step 3: Watchlist page (server component — initial SSR load only)**

`web/app/watchlist/page.tsx`:

```tsx
import { api } from "@/lib/api";
import { WatchlistClient } from "./WatchlistClient";
import type { WatchlistItem } from "@/lib/types";

export const revalidate = 900;

export default async function WatchlistPage() {
  let items: WatchlistItem[] = [];
  try {
    items = await api.watchlist.list();
  } catch {
    // Backend not reachable — client will show empty state
  }

  return <WatchlistClient initialItems={items} />;
}
```

- [ ] **Step 3: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add web/app/watchlist/
git commit -m "feat: watchlist page with add-ticker form and score table"
```

---

## Task 7: Stock Detail Page

**Files:**
- Create: `web/app/stock/[ticker]/page.tsx`

- [ ] **Step 1: Implement stock detail page**

`web/app/stock/[ticker]/page.tsx`:

```tsx
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { VerdictBadge } from "@/components/VerdictBadge";
import { ScoreBar } from "@/components/ScoreBar";
import { DriverList } from "@/components/DriverList";
import { PatternCard } from "@/components/PatternCard";
import { PriceChart } from "@/components/PriceChart";

export const revalidate = 900;

function fmt(v: number | null, suffix = "", decimals = 2): string {
  if (v === null) return "N/A";
  return `${(v * (suffix === "%" ? 100 : 1)).toFixed(decimals)}${suffix}`;
}

export default async function StockPage({ params }: { params: { ticker: string } }) {
  let stock;
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
```

- [ ] **Step 2: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add web/app/stock/
git commit -m "feat: stock detail page — chart, patterns, score cards, drivers, key ratios"
```

---

## Task 8: Screener Page

**Files:**
- Create: `web/app/screener/page.tsx`
- Create: `web/app/screener/ScreenerFilters.tsx`

- [ ] **Step 1: ScreenerFilters client component (score + verdict + sector)**

`web/app/screener/ScreenerFilters.tsx`:

```tsx
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
```

- [ ] **Step 2: Screener page (server component)**

`web/app/screener/page.tsx`:

```tsx
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
```

- [ ] **Step 3: Confirm TypeScript compiles**

```bash
cd web && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add web/app/screener/
git commit -m "feat: screener page with min-score + verdict filters"
```

---

## Task 9: Vercel Deployment

**Files:**
- Create: `web/vercel.json`
- Create: `.gitignore` additions for web/

- [ ] **Step 1: Create vercel.json**

`web/vercel.json`:

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "outputDirectory": ".next"
}
```

- [ ] **Step 2: Update root .gitignore**

Create `web/.gitignore` (Next.js standard — sits inside the `web/` directory):

```
# dependencies
node_modules/

# Next.js build output
.next/
out/

# env files
.env.local
.env.development.local
.env.test.local
.env.production.local
```

- [ ] **Step 3: Set NEXT_PUBLIC_API_URL**

In the Vercel dashboard (after connecting the repo):
- Add environment variable: `NEXT_PUBLIC_API_URL` = `https://your-app.railway.app`
- Apply to: Production, Preview, Development

- [ ] **Step 4: Deploy to Vercel**

```bash
# Option A — via Vercel CLI
npm install -g vercel
cd web
vercel --prod

# Option B — via Vercel Dashboard (recommended)
# 1. Push all commits to GitHub
# 2. Go to vercel.com → New Project → Import your GitHub repo
# 3. Set Root Directory to: web
# 4. Add env var NEXT_PUBLIC_API_URL
# 5. Click Deploy
```

Expected: Vercel gives you a URL like `https://stock-dashboard-xyz.vercel.app`

- [ ] **Step 5: Smoke test the live app**

Visit the Vercel URL and confirm:
- `/watchlist` loads with a table of tickers
- Clicking a ticker navigates to `/stock/AAPL` and shows the chart + patterns
- `/screener` loads with the filter bar and results table
- Chart patterns are shown with name, explanation, and bullish/bearish/neutral badge

- [ ] **Step 6: Final commit**

```bash
git add web/vercel.json .gitignore
git commit -m "chore: Vercel deployment config — frontend complete"
```
