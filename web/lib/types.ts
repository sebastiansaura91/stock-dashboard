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
