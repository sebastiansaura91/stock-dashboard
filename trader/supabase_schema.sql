-- Stock Dashboard — Supabase schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Safe to re-run: all statements are idempotent.

-- ─────────────────────────────────────────────
-- 1. Ticker cache
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tickers (
    ticker      TEXT PRIMARY KEY,
    data        JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Index speeds up the .eq("ticker", ...) lookup in read_cache()
CREATE INDEX IF NOT EXISTS tickers_ticker_idx ON tickers (ticker);

-- ─────────────────────────────────────────────
-- 2. Watchlist
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlist (
    ticker      TEXT PRIMARY KEY,
    added_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────
-- 3. Seed the watchlist with the default tickers
--    (matches WATCHLIST in config.py)
--    ON CONFLICT DO NOTHING makes this idempotent.
-- ─────────────────────────────────────────────
INSERT INTO watchlist (ticker) VALUES
    ('AAPL'),
    ('MSFT'),
    ('NVDA')
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- 4. Row-Level Security
--    The app uses the anon key (no auth), so we
--    enable RLS and grant full access to anon.
--    Tighten this if you add authentication later.
-- ─────────────────────────────────────────────
ALTER TABLE tickers  ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

-- Allow the anon role to read/write tickers
CREATE POLICY IF NOT EXISTS "anon full access tickers"
    ON tickers FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Allow the anon role to read/write watchlist
CREATE POLICY IF NOT EXISTS "anon full access watchlist"
    ON watchlist FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);
