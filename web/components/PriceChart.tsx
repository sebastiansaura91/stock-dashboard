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
